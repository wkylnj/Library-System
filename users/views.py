from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.utils import timezone
from datetime import timedelta
from .forms import UserRegisterForm, UserLoginForm, UserProfileForm
from .models import EmailVerificationToken, User
from .utils import send_verification_email
from books.models import BorrowRecord


def register_view(request):
    """用户注册"""
    if request.user.is_authenticated:
        return redirect('books:index')

    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # 注册后暂不激活，需要邮箱验证
            user.save()
            # 发送验证码邮件
            token = send_verification_email(user)
            if token:
                # 保存用户ID到session，用于验证码验证
                request.session['pending_user_id'] = user.id
                messages.success(request, '注册成功！验证码已发送到您的邮箱，请查收。')
            else:
                request.session['pending_user_id'] = user.id
                messages.warning(request, '注册成功，但验证码发送失败，请点击重新发送。')
            return redirect('users:verify_code')
    else:
        form = UserRegisterForm()

    return render(request, 'users/register.html', {'form': form})


def login_view(request):
    """用户登录"""
    if request.user.is_authenticated:
        return redirect('books:index')

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'欢迎回来，{user.username}！')
            next_url = request.GET.get('next', 'books:index')
            return redirect(next_url)
    else:
        form = UserLoginForm()

    return render(request, 'users/login.html', {'form': form})


@login_required
def logout_view(request):
    """用户登出"""
    logout(request)
    messages.info(request, '您已成功退出登录。')
    return redirect('users:login')


@login_required
def profile_view(request):
    """用户个人中心"""
    borrow_records = BorrowRecord.objects.filter(
        user=request.user
    ).select_related('book').order_by('-borrow_date')

    current_borrows = borrow_records.filter(status='borrowed')
    history_borrows = borrow_records.filter(status='returned')

    context = {
        'current_borrows': current_borrows,
        'history_borrows': history_borrows[:10],  # 最近10条历史记录
    }
    return render(request, 'users/profile.html', context)


@login_required
def edit_profile_view(request):
    """编辑个人资料"""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, '个人资料更新成功！')
            return redirect('users:profile')
    else:
        form = UserProfileForm(instance=request.user)

    return render(request, 'users/edit_profile.html', {'form': form})


def verification_sent_view(request):
    """验证邮件已发送页面（兼容旧链接）"""
    return redirect('users:verify_code')


def verify_code_view(request):
    """验证码输入页面"""
    # 获取待验证用户
    pending_user_id = request.session.get('pending_user_id')
    if not pending_user_id:
        messages.error(request, '请先注册账号。')
        return redirect('users:register')

    try:
        user = User.objects.get(id=pending_user_id, is_active=False)
    except User.DoesNotExist:
        messages.error(request, '用户不存在或已激活。')
        return redirect('users:register')

    if request.method == 'POST':
        code = request.POST.get('code', '').strip()

        if not code:
            messages.error(request, '请输入验证码。')
            return render(request, 'users/verify_code.html', {'email': user.email})

        # 验证验证码
        try:
            verification = EmailVerificationToken.objects.get(
                user=user,
                code=code,
                is_used=False
            )

            # 检查验证码是否过期（24小时有效）
            if timezone.now() - verification.created_at > timedelta(hours=24):
                messages.error(request, '验证码已过期，请点击重新发送。')
                return render(request, 'users/verify_code.html', {'email': user.email})

            # 激活用户
            user.is_active = True
            user.email_verified = True
            user.save()

            # 标记验证码已使用
            verification.is_used = True
            verification.save()

            # 清除session
            del request.session['pending_user_id']

            messages.success(request, '邮箱验证成功！您现在可以登录了。')
            return redirect('users:login')

        except EmailVerificationToken.DoesNotExist:
            messages.error(request, '验证码错误，请重新输入。')
            return render(request, 'users/verify_code.html', {'email': user.email})

    return render(request, 'users/verify_code.html', {'email': user.email})


def verify_email_view(request, token):
    """验证邮箱（保留旧链接兼容）"""
    try:
        verification = EmailVerificationToken.objects.get(token=token, is_used=False)
        # 检查Token是否过期（24小时有效）
        if timezone.now() - verification.created_at > timedelta(hours=24):
            messages.error(request, '验证链接已过期，请重新注册或申请新的验证邮件。')
            return redirect('users:login')

        # 激活用户
        user = verification.user
        user.is_active = True
        user.email_verified = True
        user.save()

        # 标记Token已使用
        verification.is_used = True
        verification.save()

        messages.success(request, '邮箱验证成功！您现在可以登录了。')
        return redirect('users:login')
    except EmailVerificationToken.DoesNotExist:
        messages.error(request, '无效的验证链接。')
        return redirect('users:login')


def resend_verification_view(request):
    """重新发送验证码"""
    pending_user_id = request.session.get('pending_user_id')

    if request.method == 'POST':
        # 优先使用session中的用户
        if pending_user_id:
            try:
                user = User.objects.get(id=pending_user_id, is_active=False)
                token = send_verification_email(user)
                if token:
                    messages.success(request, '验证码已重新发送，请查收邮箱。')
                else:
                    messages.error(request, '发送失败，请稍后重试。')
                return redirect('users:verify_code')
            except User.DoesNotExist:
                pass

        # 否则通过邮箱查找
        email = request.POST.get('email', '').strip()
        if email:
            try:
                user = User.objects.get(email=email, is_active=False)
                token = send_verification_email(user)
                if token:
                    request.session['pending_user_id'] = user.id
                    messages.success(request, '验证码已重新发送，请查收邮箱。')
                    return redirect('users:verify_code')
                else:
                    messages.error(request, '发送失败，请稍后重试。')
            except User.DoesNotExist:
                messages.error(request, '未找到该邮箱对应的未激活账户。')

        return redirect('users:verify_code') if pending_user_id else redirect('users:resend_verification')

    return render(request, 'users/resend_verification.html')
