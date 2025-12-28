"""
定时任务和邮件提醒功能
"""
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


def send_reminder_email(user, subject, message):
    """发送提醒邮件"""
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f'发送邮件失败: {e}')
        return False


def notify_reservation(book):
    """通知预约者有书可借"""
    from .models import Reservation

    # 获取第一个等待中的预约
    reservation = Reservation.objects.filter(
        book=book,
        status='waiting'
    ).order_by('created_at').first()

    if reservation:
        user = reservation.user
        subject = f'【图书管理系统】您预约的《{book.title}》已有库存'
        message = f'''
尊敬的 {user.username}：

您预约的图书《{book.title}》现已有库存可借，请尽快前往借阅。

预约时间：{reservation.created_at.strftime("%Y-%m-%d %H:%M")}

请在收到通知后3天内完成借阅，否则预约将自动失效。

此致
图书管理系统团队
'''
        if send_reminder_email(user, subject, message):
            reservation.status = 'notified'
            reservation.notified_at = timezone.now()
            reservation.save()
            return True

    return False


def check_due_reminders():
    """检查并发送到期提醒邮件"""
    from .models import BorrowRecord

    now = timezone.now()
    results = {
        '3_days': 0,
        '1_day': 0,
        'overdue': 0,
    }

    # 3天内到期提醒
    three_days_later = now + timedelta(days=3)
    records_3days = BorrowRecord.objects.filter(
        status='borrowed',
        due_date__lte=three_days_later,
        due_date__gt=now,
        reminder_3days_sent=False
    ).select_related('user', 'book', 'book_copy')

    for record in records_3days:
        days_left = (record.due_date - now).days
        copy_info = f' [{record.book_copy.copy_number}]' if record.book_copy else ''
        subject = f'【图书管理系统】您借阅的《{record.book.title}》即将到期'
        message = f'''
尊敬的 {record.user.username}：

您借阅的图书《{record.book.title}》{copy_info} 将于 {record.due_date.strftime("%Y-%m-%d")} 到期。

距离到期还有 {days_left} 天，请及时归还。

借阅时间：{record.borrow_date.strftime("%Y-%m-%d %H:%M")}
应还日期：{record.due_date.strftime("%Y-%m-%d")}

此致
图书管理系统团队
'''
        if send_reminder_email(record.user, subject, message):
            record.reminder_3days_sent = True
            record.save()
            results['3_days'] += 1

    # 1天内到期提醒
    one_day_later = now + timedelta(days=1)
    records_1day = BorrowRecord.objects.filter(
        status='borrowed',
        due_date__lte=one_day_later,
        due_date__gt=now,
        reminder_1day_sent=False
    ).select_related('user', 'book', 'book_copy')

    for record in records_1day:
        copy_info = f' [{record.book_copy.copy_number}]' if record.book_copy else ''
        subject = f'【图书管理系统】紧急提醒：《{record.book.title}》明天到期'
        message = f'''
尊敬的 {record.user.username}：

【紧急提醒】您借阅的图书《{record.book.title}》{copy_info} 将于明天（{record.due_date.strftime("%Y-%m-%d")}）到期。

请务必在到期前归还图书，逾期将影响您的借阅记录。

借阅时间：{record.borrow_date.strftime("%Y-%m-%d %H:%M")}
应还日期：{record.due_date.strftime("%Y-%m-%d")}

此致
图书管理系统团队
'''
        if send_reminder_email(record.user, subject, message):
            record.reminder_1day_sent = True
            record.save()
            results['1_day'] += 1

    # 逾期提醒
    records_overdue = BorrowRecord.objects.filter(
        status='borrowed',
        due_date__lt=now,
        overdue_reminder_sent=False
    ).select_related('user', 'book', 'book_copy')

    for record in records_overdue:
        days_overdue = (now - record.due_date).days
        copy_info = f' [{record.book_copy.copy_number}]' if record.book_copy else ''
        subject = f'【图书管理系统】逾期提醒：《{record.book.title}》已逾期 {days_overdue} 天'
        message = f'''
尊敬的 {record.user.username}：

您借阅的图书《{record.book.title}》{copy_info} 已逾期 {days_overdue} 天。

请尽快归还图书。

借阅时间：{record.borrow_date.strftime("%Y-%m-%d %H:%M")}
应还日期：{record.due_date.strftime("%Y-%m-%d")}
逾期天数：{days_overdue} 天

此致
图书管理系统团队
'''
        if send_reminder_email(record.user, subject, message):
            record.overdue_reminder_sent = True
            record.save()
            results['overdue'] += 1

    return results


def check_expired_reservations():
    """检查并处理过期的预约（通知后超过3天未借阅）"""
    from .models import Reservation

    now = timezone.now()
    three_days_ago = now - timedelta(days=3)

    # 将通知后超过3天的预约标记为过期
    expired = Reservation.objects.filter(
        status='notified',
        notified_at__lt=three_days_ago
    ).update(status='expired')

    return expired


def run_all_tasks():
    """运行所有定时任务"""
    results = {
        'due_reminders': check_due_reminders(),
        'expired_reservations': check_expired_reservations(),
    }
    return results
