from django.contrib import admin
from .models import Budget

@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('category', 'user', 'budget_amount', 'month', 'year', 'is_active', 'created_at')
    list_filter = ('year', 'month', 'is_active', 'category', 'user')
    search_fields = ('category__name', 'user__username', 'notes')
    ordering = ('-year', '-month', 'category__name')
    raw_id_fields = ('category', 'user')
