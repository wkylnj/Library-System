import re
from django import forms
from django.core.validators import RegexValidator
from django.utils.html import strip_tags
from .models import Book, Category, BookCopy


class BookForm(forms.ModelForm):
    """图书表单 - 包含数据验证和安全清理"""

    # ISBN 验证器
    isbn_validator = RegexValidator(
        regex=r'^(?:\d{10}|\d{13}|\d{3}-\d{10})$',
        message='ISBN 格式不正确，应为10位或13位数字'
    )

    isbn = forms.CharField(
        max_length=20,
        validators=[isbn_validator],
        label='ISBN',
        help_text='请输入10位或13位ISBN号'
    )

    # 添加副本数量字段
    copies_count = forms.IntegerField(
        min_value=1,
        max_value=100,
        initial=1,
        label='副本数量',
        help_text='将自动为每个副本生成唯一编号',
        required=False
    )

    class Meta:
        model = Book
        fields = [
            'isbn', 'title', 'author', 'publisher',
            'publish_date', 'category', 'description',
            'location'
        ]
        widgets = {
            'publish_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

        # 编辑模式下隐藏副本数量字段
        if self.instance.pk:
            self.fields['copies_count'].widget = forms.HiddenInput()
            self.fields['copies_count'].required = False

    def clean_title(self):
        """清理书名 - 防止XSS攻击"""
        title = self.cleaned_data.get('title', '')
        # 移除HTML标签
        title = strip_tags(title)
        # 移除多余空格
        title = ' '.join(title.split())
        if len(title) < 1:
            raise forms.ValidationError('书名不能为空')
        if len(title) > 200:
            raise forms.ValidationError('书名不能超过200个字符')
        return title

    def clean_author(self):
        """清理作者名 - 防止XSS攻击"""
        author = self.cleaned_data.get('author', '')
        author = strip_tags(author)
        author = ' '.join(author.split())
        if len(author) < 1:
            raise forms.ValidationError('作者不能为空')
        return author

    def clean_publisher(self):
        """清理出版社"""
        publisher = self.cleaned_data.get('publisher', '')
        if publisher:
            publisher = strip_tags(publisher)
        return publisher

    def clean_description(self):
        """清理简介 - 防止XSS攻击"""
        description = self.cleaned_data.get('description', '')
        if description:
            # 移除HTML标签但保留换行
            description = strip_tags(description)
        return description

    def clean_location(self):
        """清理存放位置"""
        location = self.cleaned_data.get('location', '')
        if location:
            location = strip_tags(location)
        return location

    def clean_isbn(self):
        """验证ISBN唯一性"""
        isbn = self.cleaned_data.get('isbn', '')
        # 移除可能的连字符
        isbn = isbn.replace('-', '')

        # 检查是否已存在（排除当前编辑的图书）
        existing = Book.objects.filter(isbn=isbn)
        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise forms.ValidationError('该ISBN已被其他图书使用')

        return isbn

    def save(self, commit=True):
        book = super().save(commit=commit)

        # 如果是新建图书，创建副本
        if commit and not self.instance.pk:
            copies_count = self.cleaned_data.get('copies_count', 1) or 1
            for i in range(copies_count):
                BookCopy.objects.create(book=book)

        return book


class BookCopyForm(forms.ModelForm):
    """图书副本表单"""
    class Meta:
        model = BookCopy
        fields = ['copy_number', 'status', 'condition', 'notes']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class BookSearchForm(forms.Form):
    """图书搜索表单 - 防止SQL注入"""
    keyword = forms.CharField(
        required=False,
        label='关键词',
        max_length=100,  # 限制搜索关键词长度
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '搜索书名、作者、ISBN...'
        })
    )
    category = forms.ModelChoiceField(
        required=False,
        queryset=Category.objects.all(),
        label='分类',
        empty_label='所有分类',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    def clean_keyword(self):
        """清理搜索关键词"""
        keyword = self.cleaned_data.get('keyword', '')
        if keyword:
            # 移除HTML标签
            keyword = strip_tags(keyword)
            # 移除可能的SQL注入字符
            keyword = re.sub(r'[;\'\"\\]', '', keyword)
        return keyword


class CategoryForm(forms.ModelForm):
    """分类表单 - 包含数据验证"""
    class Meta:
        model = Category
        fields = ['name', 'description']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def clean_name(self):
        """清理分类名称"""
        name = self.cleaned_data.get('name', '')
        name = strip_tags(name)
        name = ' '.join(name.split())

        if len(name) < 1:
            raise forms.ValidationError('分类名称不能为空')

        # 检查唯一性
        existing = Category.objects.filter(name=name)
        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise forms.ValidationError('该分类名称已存在')

        return name

    def clean_description(self):
        """清理分类描述"""
        description = self.cleaned_data.get('description', '')
        if description:
            description = strip_tags(description)
        return description
