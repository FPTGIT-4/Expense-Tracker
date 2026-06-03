from django.contrib import admin
from .models import Income

@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ('user', 'source', 'amount', 'date', 'created_at')
    list_filter = ('source', 'date', 'user')
    search_fields = ('source', 'description', 'user__username')
    ordering = ('-date', '-created_at')
