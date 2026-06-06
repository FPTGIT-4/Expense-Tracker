from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal

from income.models import Income
from expenses.models import Expense
from categories.models import Category

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = timezone.localdate()

        # Summary statistics
        total_income = Income.objects.filter(user=user).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        total_expenses = Expense.objects.filter(user=user).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        current_balance = total_income - total_expenses
        total_categories = Category.objects.filter(user=user).count()

        # Today's statistics
        income_today = Income.objects.filter(user=user, date=today).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        expenses_today = Expense.objects.filter(user=user, date=today).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # Recent transactions (fetch up to 4 for each type, sorted)
        db_incomes = Income.objects.filter(user=user).order_by('-date', '-created_at')[:4]
        db_expenses = Expense.objects.filter(user=user).select_related('category').order_by('-date', '-created_at')[:4]

        recent_incomes = []
        for inc in db_incomes:
            recent_incomes.append({
                'date': inc.date,
                'created_at': inc.created_at,
                'type': 'Income',
                'amount': inc.amount,
                'category_or_source': inc.source,
                'description': inc.description,
            })

        recent_expenses = []
        for exp in db_expenses:
            recent_expenses.append({
                'date': exp.date,
                'created_at': exp.created_at,
                'type': 'Expense',
                'amount': exp.amount,
                'category_or_source': exp.category.name if exp.category else 'Uncategorized',
                'description': exp.description,
            })

        # Combined transactions
        all_transactions = recent_incomes + recent_expenses
        all_transactions.sort(key=lambda x: (x['date'], x['created_at']), reverse=True)
        recent_transactions = all_transactions[:4]

        # Context variables
        context.update({
            'today': today,
            'total_income': total_income,
            'total_expenses': total_expenses,
            'current_balance': current_balance,
            'total_categories': total_categories,
            'income_today': income_today,
            'expenses_today': expenses_today,
            'recent_transactions': recent_transactions,
            'recent_incomes': recent_incomes,
            'recent_expenses': recent_expenses,
            'source_choices': Income.SOURCE_CHOICES,
            'categories': Category.objects.filter(user=user).order_by('name'),
        })

        return context

    def post(self, request, *args, **kwargs):
        return redirect('dashboard')
