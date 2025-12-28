"""
使用AI生成图书封面
"""
import os
import time
import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files.base import ContentFile
from books.models import Book


class Command(BaseCommand):
    help = '使用AI生成图书封面'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制重新生成所有封面',
        )

    def generate_cover_prompt(self, book):
        """根据图书信息生成封面提示词"""
        category_style = {
            '计算机': 'modern tech style, circuit patterns, blue and white colors',
            '文学': 'elegant literary style, classic design, warm colors',
            '历史': 'vintage historical style, ancient textures, sepia tones',
            '哲学': 'philosophical abstract style, deep colors, minimalist',
            '心理学': 'mind and brain imagery, soft colors, professional',
            '经济': 'business professional style, charts and graphs, gold and navy',
            '科学': 'scientific illustration style, cosmos and atoms, vibrant',
            '艺术': 'artistic creative style, colorful, expressive brushstrokes',
        }

        cat_name = book.category.name if book.category else '文学'
        style = category_style.get(cat_name, 'elegant book cover design, professional')

        prompt = f"Book cover design for '{book.title}' by {book.author}, {style}, high quality, professional publishing standard, no text"
        return prompt

    def generate_cover_with_dashscope(self, book):
        """使用DashScope API生成封面"""
        api_key = getattr(settings, 'AI_API_KEY', None)
        if not api_key:
            return None

        prompt = self.generate_cover_prompt(book)

        # DashScope 图像生成 API
        url = 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis'

        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'X-DashScope-Async': 'enable'
        }

        data = {
            'model': 'wanx-v1',
            'input': {
                'prompt': prompt
            },
            'parameters': {
                'size': '720*1280',
                'n': 1,
                'style': '<auto>'
            }
        }

        try:
            # 提交任务
            response = requests.post(url, headers=headers, json=data, timeout=30)
            result = response.json()

            self.stdout.write(f'  API响应: {result.get("output", {}).get("task_status", "unknown")}')

            if 'output' not in result or 'task_id' not in result['output']:
                self.stdout.write(self.style.WARNING(f'  任务创建失败: {result}'))
                return None

            task_id = result['output']['task_id']

            # 轮询获取结果
            check_url = f'https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}'
            for i in range(30):  # 最多等待60秒
                time.sleep(3)
                check_response = requests.get(check_url, headers={'Authorization': f'Bearer {api_key}'})
                check_result = check_response.json()

                status = check_result.get('output', {}).get('task_status')
                self.stdout.write(f'  轮询 {i+1}: {status}')

                if status == 'SUCCEEDED':
                    results = check_result.get('output', {}).get('results', [])
                    if results and 'url' in results[0]:
                        image_url = results[0]['url']
                        # 下载图片
                        img_response = requests.get(image_url, timeout=30)
                        if img_response.status_code == 200:
                            return img_response.content
                    break
                elif status == 'FAILED':
                    error_msg = check_result.get('output', {}).get('message', '未知错误')
                    self.stdout.write(self.style.WARNING(f'  生成失败: {error_msg}'))
                    break

            return None
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  API错误: {e}'))
            return None

    def handle(self, *args, **options):
        force = options['force']

        books = Book.objects.all()
        if not force:
            books = books.filter(cover='')

        total = books.count()
        self.stdout.write(f'需要生成封面的图书: {total} 本')

        for i, book in enumerate(books, 1):
            self.stdout.write(f'[{i}/{total}] 正在为《{book.title}》生成封面...')

            image_data = self.generate_cover_with_dashscope(book)

            if image_data:
                filename = f'{book.id}_{book.isbn}.png'
                book.cover.save(filename, ContentFile(image_data), save=True)
                self.stdout.write(self.style.SUCCESS(f'  封面已保存'))
            else:
                self.stdout.write(self.style.WARNING(f'  跳过'))

            # 避免API限流
            time.sleep(1)

        self.stdout.write(self.style.SUCCESS('完成!'))
