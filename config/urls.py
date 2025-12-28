"""
URL configuration for library_system project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from books import views as books_views

urlpatterns = [
    # 管理员功能（放在 Django admin 之前）
    path('admin/dashboard/', books_views.admin_dashboard, name='admin_dashboard'),
    path('admin/records/', books_views.all_borrow_records, name='all_borrow_records'),

    # Django admin
    path('admin/', admin.site.urls),

    # 应用路由
    path('', include('books.urls')),
    path('users/', include('users.urls')),
]

# 开发环境下提供媒体文件服务
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
