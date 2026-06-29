from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal
from datetime import timedelta

from income.models import Income
from expenses.models import Expense
from categories.models import Category
from accounts.models import Account

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = timezone.localdate()

        # Summary statistics
        total_income = Income.objects.filter(user=user).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        total_expenses = Expense.objects.filter(user=user).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Ensure user has at least one account
        if not Account.objects.filter(user=user).exists():
            Account.objects.create(
                user=user,
                name='Cash',
                account_type='Cash',
                initial_balance=Decimal('0.00')
            )
        
        from accounts.models import annotate_balance
        accounts = list(annotate_balance(Account.objects.filter(user=user).order_by('name')))
        total_balance = sum(acc.current_balance for acc in accounts)
        total_categories = Category.objects.filter(user=user).count()

        # Context variables
        context.update({
            'today': today,
            'total_income': total_income,
            'total_expenses': total_expenses,
            'total_balance': total_balance,
            'total_categories': total_categories,
        })

        return context

    def post(self, request, *args, **kwargs):
        return redirect('dashboard')
