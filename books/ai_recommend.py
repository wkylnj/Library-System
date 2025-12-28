"""
AI 图书推荐服务
基于用户借阅历史和偏好进行智能推荐
"""
import json
import requests
from django.conf import settings
from django.db.models import Count, Q
from .models import Book, BorrowRecord, Category


class AIRecommendService:
    """AI 推荐服务类"""

    def __init__(self):
        # 可配置的 AI API 设置
        self.api_key = getattr(settings, 'AI_API_KEY', None)
        self.api_url = getattr(settings, 'AI_API_URL', 'https://api.deepseek.com/v1/chat/completions')
        self.model = getattr(settings, 'AI_MODEL', 'deepseek-chat')

    def get_user_reading_profile(self, user):
        """获取用户阅读画像"""
        borrow_records = BorrowRecord.objects.filter(user=user).select_related('book', 'book__category')

        if not borrow_records.exists():
            return None

        # 统计用户借阅的分类
        category_counts = {}
        authors = []
        books_borrowed = []

        for record in borrow_records:
            book = record.book
            books_borrowed.append(book.title)

            if book.category:
                cat_name = book.category.name
                category_counts[cat_name] = category_counts.get(cat_name, 0) + 1

            if book.author:
                authors.append(book.author)

        # 找出最喜欢的分类
        favorite_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:3]

        return {
            'books_borrowed': books_borrowed,
            'favorite_categories': [cat[0] for cat in favorite_categories],
            'favorite_authors': list(set(authors))[:5],
            'total_borrowed': len(books_borrowed),
        }

    def get_available_books(self):
        """获取所有可借阅的图书信息"""
        # 使用注解查询可借阅副本数量
        books = Book.objects.annotate(
            avail_copies=Count('copies', filter=Q(copies__status='available'))
        ).filter(avail_copies__gt=0).select_related('category')
        return [
            {
                'id': book.id,
                'title': book.title,
                'author': book.author,
                'category': book.category.name if book.category else '未分类',
                'description': book.description[:100] if book.description else '',
            }
            for book in books
        ]

    def build_recommendation_prompt(self, user_profile, available_books, user_input=None):
        """构建推荐提示词"""
        books_info = "\n".join([
            f"- 《{b['title']}》 作者: {b['author']}, 分类: {b['category']}"
            for b in available_books[:50]  # 限制数量避免超长
        ])

        if user_profile:
            profile_info = f"""
用户阅读画像:
- 已借阅过的书籍: {', '.join(user_profile['books_borrowed'][:10])}
- 偏好分类: {', '.join(user_profile['favorite_categories'])}
- 喜欢的作者: {', '.join(user_profile['favorite_authors'][:5])}
- 总借阅数: {user_profile['total_borrowed']}
"""
        else:
            profile_info = "用户是新用户，暂无借阅历史。"

        user_request = f"\n用户的具体需求: {user_input}" if user_input else ""

        prompt = f"""你是一个专业的图书馆推荐系统。请根据用户的阅读历史和偏好，从图书馆现有藏书中推荐最适合的书籍。

{profile_info}
{user_request}

图书馆现有可借阅书籍:
{books_info}

请推荐5本最适合该用户的书籍，并说明推荐理由。

要求:
1. 只能从上述图书馆现有书籍中推荐
2. 不要推荐用户已经借阅过的书籍
3. 推荐要考虑用户的阅读偏好和兴趣
4. 每本书给出简短的推荐理由

请按以下JSON格式返回（只返回JSON，不要其他内容）:
{{
    "recommendations": [
        {{
            "title": "书名",
            "reason": "推荐理由"
        }}
    ],
    "summary": "整体推荐总结（一句话）"
}}
"""
        return prompt

    def call_ai_api(self, prompt):
        """调用 AI API"""
        if not self.api_key:
            return None

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }

        data = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': '你是一个专业的图书推荐助手，善于根据用户喜好推荐合适的书籍。'},
                {'role': 'user', 'content': prompt}
            ],
            'temperature': 0.7,
            'max_tokens': 1000
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            content = result['choices'][0]['message']['content']
            # 尝试解析 JSON
            # 移除可能的 markdown 代码块标记
            content = content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.startswith('```'):
                content = content[3:]
            if content.endswith('```'):
                content = content[:-3]
            return json.loads(content.strip())
        except Exception as e:
            print(f"AI API 调用失败: {e}")
            return None

    def get_recommendations(self, user, user_input=None):
        """获取推荐结果"""
        user_profile = self.get_user_reading_profile(user) if user.is_authenticated else None
        available_books = self.get_available_books()

        if not available_books:
            return {
                'success': False,
                'message': '图书馆暂无可借阅的书籍',
                'recommendations': []
            }

        # 尝试调用 AI API
        if self.api_key:
            prompt = self.build_recommendation_prompt(user_profile, available_books, user_input)
            ai_result = self.call_ai_api(prompt)

            if ai_result:
                # 匹配图书 ID
                recommendations = []
                for rec in ai_result.get('recommendations', []):
                    book = Book.objects.filter(title__icontains=rec['title']).first()
                    if book:
                        recommendations.append({
                            'book': book,
                            'reason': rec['reason']
                        })

                return {
                    'success': True,
                    'message': ai_result.get('summary', 'AI 为您精选的推荐'),
                    'recommendations': recommendations,
                    'is_ai': True
                }

        # 如果 AI 不可用，使用基于规则的推荐
        return self.get_rule_based_recommendations(user_profile, available_books)

    def get_rule_based_recommendations(self, user_profile, available_books):
        """基于规则的推荐（AI 不可用时的备选方案）"""
        recommendations = []
        borrowed_titles = set(user_profile['books_borrowed']) if user_profile else set()

        if user_profile and user_profile['favorite_categories']:
            # 推荐用户喜欢的分类中的书
            for cat in user_profile['favorite_categories']:
                books = Book.objects.annotate(
                    avail_copies=Count('copies', filter=Q(copies__status='available'))
                ).filter(
                    category__name=cat,
                    avail_copies__gt=0
                ).exclude(title__in=borrowed_titles)[:2]

                for book in books:
                    recommendations.append({
                        'book': book,
                        'reason': f'根据您对"{cat}"类书籍的喜好推荐'
                    })

        # 补充热门书籍
        if len(recommendations) < 5:
            popular_books = Book.objects.annotate(
                avail_copies=Count('copies', filter=Q(copies__status='available')),
                total_copy_count=Count('copies')
            ).filter(
                avail_copies__gt=0
            ).exclude(
                title__in=borrowed_titles
            ).exclude(
                id__in=[r['book'].id for r in recommendations]
            ).order_by('-total_copy_count')[:5 - len(recommendations)]

            for book in popular_books:
                recommendations.append({
                    'book': book,
                    'reason': '图书馆热门藏书推荐'
                })

        return {
            'success': True,
            'message': '根据您的阅读偏好为您推荐',
            'recommendations': recommendations[:5],
            'is_ai': False
        }

    def get_similar_books(self, book):
        """获取相似书籍推荐"""
        similar = []

        # 同分类的书
        if book.category:
            same_category = Book.objects.annotate(
                avail_copies=Count('copies', filter=Q(copies__status='available'))
            ).filter(
                category=book.category,
                avail_copies__gt=0
            ).exclude(id=book.id)[:3]
            for b in same_category:
                similar.append({
                    'book': b,
                    'reason': f'同属"{book.category.name}"分类'
                })

        # 同作者的书
        same_author = Book.objects.annotate(
            avail_copies=Count('copies', filter=Q(copies__status='available'))
        ).filter(
            author=book.author,
            avail_copies__gt=0
        ).exclude(id=book.id)[:2]
        for b in same_author:
            similar.append({
                'book': b,
                'reason': f'同为{book.author}的作品'
            })

        return similar[:5]
