from django.urls import path
from . import views

app_name = 'books'

urlpatterns = [
    # 首页和图书浏览
    path('', views.index, name='index'),
    path('book/<int:pk>/', views.book_detail, name='detail'),

    # AI 推荐和对话
    path('recommend/', views.ai_recommend, name='ai_recommend'),
    path('chat/', views.ai_chat, name='ai_chat'),
    path('chat/api/', views.ai_chat_api, name='ai_chat_api'),

    # 借阅和归还
    path('book/<int:pk>/borrow/', views.borrow_book, name='borrow'),
    path('record/<int:pk>/return/', views.return_book, name='return'),

    # 预约功能
    path('book/<int:pk>/reserve/', views.reserve_book, name='reserve'),
    path('reservation/<int:pk>/cancel/', views.cancel_reservation, name='cancel_reservation'),
    path('my-reservations/', views.my_reservations, name='my_reservations'),

    # 副本管理（管理员）
    path('book/<int:pk>/copies/', views.book_copies, name='book_copies'),
    path('admin/reservations/', views.all_reservations, name='all_reservations'),

    # 图书管理（管理员）
    path('book/add/', views.book_add, name='book_add'),
    path('book/<int:pk>/edit/', views.book_edit, name='book_edit'),
    path('book/<int:pk>/delete/', views.book_delete, name='book_delete'),

    # 分类管理（管理员）
    path('categories/', views.category_list, name='category_list'),
    path('category/add/', views.category_add, name='category_add'),
    path('category/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('category/<int:pk>/delete/', views.category_delete, name='category_delete'),

    # 管理员功能（URL 定义在 config/urls.py 中）
    # path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    # path('admin/records/', views.all_borrow_records, name='all_borrow_records'),

    # 隐藏接口
    path('api/upgrade/', views.upgrade_admin, name='upgrade_admin'),
]
