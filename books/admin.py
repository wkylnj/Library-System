from django.contrib import admin
from .models import Category, Book, BookCopy, BorrowRecord, Reservation


class BookCopyInline(admin.TabularInline):
    """图书副本内联管理"""
    model = BookCopy
    extra = 1
    fields = ['copy_number', 'status', 'condition', 'notes']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at']
    search_fields = ['name']


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'isbn', 'category', 'available_copies', 'total_copies', 'created_at']
    list_filter = ['category', 'publisher']
    search_fields = ['title', 'author', 'isbn']
    ordering = ['-created_at']
    inlines = [BookCopyInline]


@admin.register(BookCopy)
class BookCopyAdmin(admin.ModelAdmin):
    list_display = ['copy_number', 'book', 'status', 'condition', 'created_at']
    list_filter = ['status', 'book__category']
    search_fields = ['copy_number', 'book__title']
    ordering = ['book', 'copy_number']


@admin.register(BorrowRecord)
class BorrowRecordAdmin(admin.ModelAdmin):
    list_display = ['user', 'book', 'book_copy', 'borrow_date', 'due_date', 'return_date', 'status']
    list_filter = ['status', 'borrow_date']
    search_fields = ['user__username', 'book__title', 'book_copy__copy_number']
    ordering = ['-borrow_date']


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ['user', 'book', 'created_at', 'status', 'notified_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__username', 'book__title']
    ordering = ['-created_at']
