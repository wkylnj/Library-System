"""
定时任务管理命令

使用方法：
python manage.py run_tasks

可以通过 cron 定时执行：
# 每天上午9点执行
0 9 * * * cd /root/website_homework/library_system && /usr/bin/python manage.py run_tasks >> /var/log/library_tasks.log 2>&1
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from books.tasks import run_all_tasks


class Command(BaseCommand):
    help = '运行图书管理系统的定时任务（到期提醒、预约过期检查等）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='仅显示将要执行的操作，不实际发送邮件',
        )

    def handle(self, *args, **options):
        self.stdout.write(f'[{timezone.now().strftime("%Y-%m-%d %H:%M:%S")}] 开始执行定时任务...')

        if options['dry_run']:
            self.stdout.write(self.style.WARNING('干运行模式，不会实际发送邮件'))

        try:
            results = run_all_tasks()

            # 输出到期提醒结果
            due_results = results.get('due_reminders', {})
            self.stdout.write(f'  - 3天到期提醒: 发送 {due_results.get("3_days", 0)} 封')
            self.stdout.write(f'  - 1天到期提醒: 发送 {due_results.get("1_day", 0)} 封')
            self.stdout.write(f'  - 逾期提醒: 发送 {due_results.get("overdue", 0)} 封')

            # 输出预约过期结果
            expired = results.get('expired_reservations', 0)
            self.stdout.write(f'  - 过期预约处理: {expired} 条')

            self.stdout.write(self.style.SUCCESS(
                f'[{timezone.now().strftime("%Y-%m-%d %H:%M:%S")}] 定时任务执行完成'
            ))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'任务执行失败: {e}'))
            raise
