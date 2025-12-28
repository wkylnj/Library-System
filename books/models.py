from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from datetime import timedelta
from django.utils import timezone


class Category(models.Model):
    """图书分类"""
    name = models.CharField(max_length=100, unique=True, verbose_name='分类名称')
    description = models.TextField(blank=True, verbose_name='描述')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '图书分类'
        verbose_name_plural = '图书分类'
        ordering = ['name']

    def __str__(self):
        return self.name

    def clean(self):
        """验证分类数据"""
        if self.name:
            self.name = self.name.strip()
            if len(self.name) > 100:
                raise ValidationError({'name': '分类名称不能超过100个字符'})


class Book(models.Model):
    """图书模型"""
    isbn = models.CharField(max_length=20, unique=True, verbose_name='ISBN')
    title = models.CharField(max_length=200, verbose_name='书名')
    author = models.CharField(max_length=200, verbose_name='作者')
    publisher = models.CharField(max_length=200, blank=True, verbose_name='出版社')
    publish_date = models.DateField(null=True, blank=True, verbose_name='出版日期')
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='分类'
    )
    description = models.TextField(blank=True, verbose_name='简介')
    cover = models.ImageField(upload_to='covers/', blank=True, null=True, verbose_name='封面')
    location = models.CharField(max_length=100, blank=True, verbose_name='存放位置')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='添加时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '图书'
        verbose_name_plural = '图书'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} - {self.author}'

    @property
    def total_copies(self):
        """总副本数"""
        return self.copies.count()

    @property
    def available_copies(self):
        """可借副本数"""
        return self.copies.filter(status='available').count()

    @property
    def borrowed_copies(self):
        """已借出副本数"""
        return self.copies.filter(status='borrowed').count()

    def is_available(self):
        return self.available_copies > 0

    def get_available_copy(self):
        """获取一本可借的副本"""
        return self.copies.filter(status='available').first()

    def clean(self):
        """验证图书数据"""
        errors = {}

        # 验证ISBN格式
        if self.isbn:
            isbn_clean = self.isbn.replace('-', '')
            if not isbn_clean.isdigit() or len(isbn_clean) not in [10, 13]:
                errors['isbn'] = 'ISBN 格式不正确'

        # 验证出版日期不能是未来
        if self.publish_date and self.publish_date > timezone.now().date():
            errors['publish_date'] = '出版日期不能是未来日期'

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        # 清理数据
        if self.title:
            self.title = self.title.strip()
        if self.author:
            self.author = self.author.strip()
        if self.isbn:
            self.isbn = self.isbn.strip()
        super().save(*args, **kwargs)


class BookCopy(models.Model):
    """图书副本模型 - 每本实体书"""
    STATUS_CHOICES = [
        ('available', '可借阅'),
        ('borrowed', '已借出'),
        ('reserved', '已预约'),
        ('maintenance', '维护中'),
        ('lost', '已丢失'),
    ]

    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='copies',
        verbose_name='图书'
    )
    copy_number = models.CharField(max_length=50, verbose_name='副本编号')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='available',
        verbose_name='状态'
    )
    condition = models.CharField(max_length=50, blank=True, default='良好', verbose_name='品相')
    notes = models.TextField(blank=True, verbose_name='备注')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='入库时间')

    class Meta:
        verbose_name = '图书副本'
        verbose_name_plural = '图书副本'
        unique_together = ['book', 'copy_number']
        ordering = ['book', 'copy_number']

    def __str__(self):
        return f'{self.book.title} [{self.copy_number}]'

    def save(self, *args, **kwargs):
        # 如果没有副本编号，自动生成
        if not self.copy_number:
            existing_count = BookCopy.objects.filter(book=self.book).count()
            self.copy_number = f'{self.book.id:04d}-{existing_count + 1:03d}'
        super().save(*args, **kwargs)


class BorrowRecord(models.Model):
    """借阅记录"""
    STATUS_CHOICES = [
        ('borrowed', '借阅中'),
        ('returned', '已归还'),
        ('overdue', '已逾期'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='borrow_records',
        verbose_name='借阅人'
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='borrow_records',
        verbose_name='图书'
    )
    book_copy = models.ForeignKey(
        BookCopy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='borrow_records',
        verbose_name='图书副本'
    )
    borrow_date = models.DateTimeField(auto_now_add=True, verbose_name='借阅日期')
    due_date = models.DateTimeField(verbose_name='应还日期')
    return_date = models.DateTimeField(null=True, blank=True, verbose_name='归还日期')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='borrowed',
        verbose_name='状态'
    )
    notes = models.TextField(blank=True, verbose_name='备注')
    # 邮件提醒标记
    reminder_3days_sent = models.BooleanField(default=False, verbose_name='3天提醒已发送')
    reminder_1day_sent = models.BooleanField(default=False, verbose_name='1天提醒已发送')
    overdue_reminder_sent = models.BooleanField(default=False, verbose_name='逾期提醒已发送')

    class Meta:
        verbose_name = '借阅记录'
        verbose_name_plural = '借阅记录'
        ordering = ['-borrow_date']

    def __str__(self):
        copy_info = f' [{self.book_copy.copy_number}]' if self.book_copy else ''
        return f'{self.user.username} 借阅 {self.book.title}{copy_info}'

    def save(self, *args, **kwargs):
        if not self.due_date:
            # 默认借阅期限30天
            self.due_date = timezone.now() + timedelta(days=30)
        super().save(*args, **kwargs)

    def is_overdue(self):
        if self.status == 'returned':
            return False
        return timezone.now() > self.due_date

    def days_remaining(self):
        if self.status == 'returned':
            return 0
        delta = self.due_date - timezone.now()
        return delta.days


class Reservation(models.Model):
    """预约记录"""
    STATUS_CHOICES = [
        ('waiting', '等待中'),
        ('notified', '已通知'),
        ('fulfilled', '已完成'),
        ('cancelled', '已取消'),
        ('expired', '已过期'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reservations',
        verbose_name='预约人'
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='reservations',
        verbose_name='图书'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='预约时间')
    notified_at = models.DateTimeField(null=True, blank=True, verbose_name='通知时间')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='waiting',
        verbose_name='状态'
    )
    notes = models.TextField(blank=True, verbose_name='备注')

    class Meta:
        verbose_name = '预约记录'
        verbose_name_plural = '预约记录'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.user.username} 预约 {self.book.title}'

    @property
    def queue_position(self):
        """获取在等待队列中的位置"""
        if self.status != 'waiting':
            return None
        return Reservation.objects.filter(
            book=self.book,
            status='waiting',
            created_at__lt=self.created_at
        ).count() + 1
