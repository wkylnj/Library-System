from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid
import random
import string


class User(AbstractUser):
    """自定义用户模型"""
    ROLE_CHOICES = [
        ('user', '普通用户'),
        ('admin', '管理员'),
    ]

    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='user',
        verbose_name='角色'
    )
    phone = models.CharField(max_length=20, blank=True, verbose_name='电话')
    email_verified = models.BooleanField(default=False, verbose_name='邮箱已验证')

    class Meta:
        verbose_name = '用户'
        verbose_name_plural = '用户'

    def __str__(self):
        return self.username

    def is_admin(self):
        return self.role == 'admin' or self.is_superuser


def generate_verification_code():
    """生成6位数字验证码"""
    return ''.join(random.choices(string.digits, k=6))


class EmailVerificationToken(models.Model):
    """邮箱验证Token"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='用户')
    token = models.UUIDField(default=uuid.uuid4, unique=True, verbose_name='Token')
    code = models.CharField(max_length=6, default=generate_verification_code, verbose_name='验证码')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    is_used = models.BooleanField(default=False, verbose_name='是否已使用')

    class Meta:
        verbose_name = '邮箱验证Token'
        verbose_name_plural = '邮箱验证Token'

    def __str__(self):
        return f'{self.user.username} - {self.code}'
