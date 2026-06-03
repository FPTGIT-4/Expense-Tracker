from django.contrib import admin
from .models import Income, Expense

@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ('user', 'source', 'amount', 'date', 'created_at')
    list_filter = ('source', 'date', 'user')
    search_fields = ('source', 'description', 'user__username')
    ordering = ('-date', '-created_at')

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'amount', 'date', 'created_at')
    list_filter = ('date', 'user')
    search_fields = ('name', 'description', 'user__username')
    ordering = ('-date', '-created_at')
