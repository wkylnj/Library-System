from django.core.mail import send_mail
from django.conf import settings
from .models import EmailVerificationToken


def send_verification_email(user, request=None):
    """发送验证码邮件"""
    # 删除该用户之前未使用的验证码
    EmailVerificationToken.objects.filter(user=user, is_used=False).delete()

    # 创建新的验证Token（包含验证码）
    token = EmailVerificationToken.objects.create(user=user)

    # 邮件内容
    subject = '【图书管理系统】邮箱验证码'
    message = f'''
尊敬的 {user.username}：

感谢您注册图书管理系统！

您的邮箱验证码是：{token.code}

验证码有效期为24小时，请尽快完成验证。

如果您没有注册过此账号，请忽略此邮件。

此致
图书管理系统团队
'''

    # 发送邮件
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        return token
    except Exception as e:
        print(f'发送邮件失败: {e}')
        return None
