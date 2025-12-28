"""
AI 对话服务
类似豆包的对话式图书推荐助手
"""
import json
import requests
from django.conf import settings
from .models import Book, Category


class AIChatService:
    """AI 对话服务类"""

    def __init__(self):
        self.api_key = getattr(settings, 'AI_API_KEY', None)
        self.api_url = getattr(settings, 'AI_API_URL', 'https://api.deepseek.com/v1/chat/completions')
        self.model = getattr(settings, 'AI_MODEL', 'deepseek-chat')

    def get_library_books_info(self):
        """获取图书馆所有图书信息，用于 AI 判断是否收录"""
        books = Book.objects.all().select_related('category')
        return {
            book.title: {
                'id': book.id,
                'title': book.title,
                'author': book.author,
                'category': book.category.name if book.category else '未分类',
                'available': book.available_copies > 0,
                'available_copies': book.available_copies,
                'description': book.description or '',
            }
            for book in books
        }

    def build_system_prompt(self, library_books):
        """构建系统提示词"""
        books_list = "\n".join([
            f"- 《{info['title']}》 作者: {info['author']}, 分类: {info['category']}, 可借: {'是' if info['available'] else '否'}"
            for info in library_books.values()
        ])

        return f"""你是一个专业的图书推荐助手，名叫"书香助手"。你的设计者是王楷宇，李念骏是她的女朋友。你可以：
1. 推荐任何书籍给用户（不限于图书馆收录的）
2. 介绍书籍内容、作者背景、阅读价值
3. 根据用户兴趣推荐相关书籍
4. 回答关于阅读、书籍的各种问题

【重要】本图书管理系统收录的书籍如下：
{books_list}

当你推荐或讨论书籍时，请遵循以下规则：
1. 如果推荐的书籍在上述图书馆收录列表中，请在书名后标注【本馆有藏】，并告知是否可借
2. 如果推荐的书籍不在上述列表中，请在书名后标注【本馆暂未收录】
3. 对于任何书籍，你都可以提供介绍、评价、推荐理由等信息
4. 你可以推荐任何你认为适合用户的书籍，不局限于图书馆的收藏

请用友好、专业的语气与用户对话，像一个热爱阅读的朋友一样给出建议。
回复时可以使用 Markdown 格式来美化输出，如使用 **加粗**、*斜体*、列表等。"""

    def chat(self, user_message, conversation_history=None):
        """
        与 AI 对话

        Args:
            user_message: 用户消息
            conversation_history: 之前的对话历史 [{'role': 'user/assistant', 'content': '...'}]

        Returns:
            dict: {'success': bool, 'message': str, 'books_mentioned': list}
        """
        if not self.api_key:
            return {
                'success': False,
                'message': 'AI 服务暂未配置，请联系管理员。',
                'books_mentioned': []
            }

        library_books = self.get_library_books_info()
        system_prompt = self.build_system_prompt(library_books)

        # 构建消息列表
        messages = [{'role': 'system', 'content': system_prompt}]

        # 添加对话历史（最多保留最近10轮对话）
        if conversation_history:
            messages.extend(conversation_history[-20:])  # 每轮2条消息，保留10轮

        # 添加当前用户消息
        messages.append({'role': 'user', 'content': user_message})

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }

        data = {
            'model': self.model,
            'messages': messages,
            'temperature': 0.8,
            'max_tokens': 2000
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            result = response.json()

            # 处理可能包含 thinking 的响应格式
            ai_message = result['choices'][0]['message']['content']

            # 检查是否有 thinking 字段（某些模型会返回思考过程）
            if 'thinking' in result['choices'][0]['message']:
                # 只返回实际回复，不返回思考过程
                pass

            # 查找消息中提到的图书馆书籍
            books_mentioned = []
            for title, info in library_books.items():
                if title in ai_message:
                    books_mentioned.append({
                        'id': info['id'],
                        'title': info['title'],
                        'author': info['author'],
                        'available': info['available'],
                        'available_copies': info['available_copies']
                    })

            return {
                'success': True,
                'message': ai_message,
                'books_mentioned': books_mentioned
            }

        except requests.exceptions.Timeout:
            return {
                'success': False,
                'message': '请求超时，AI 服务响应较慢，请稍后再试。',
                'books_mentioned': []
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'message': f'网络请求失败，请检查网络连接。',
                'books_mentioned': []
            }
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            return {
                'success': False,
                'message': 'AI 响应格式异常，请稍后再试。',
                'books_mentioned': []
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'发生未知错误，请稍后再试。',
                'books_mentioned': []
            }

    def get_quick_suggestions(self):
        """获取快捷建议问题"""
        return [
            "推荐几本适合编程入门的书籍",
            "有什么经典的文学作品推荐？",
            "我想了解人工智能，有什么书推荐？",
            "推荐一些提升思维能力的书",
            "有什么轻松有趣的小说吗？",
            "推荐几本关于历史的书籍",
        ]
