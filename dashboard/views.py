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
from .forms import DashboardIncomeForm, DashboardExpenseForm

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

        # Recent transactions
        recent_incomes = Income.objects.filter(user=user)[:5]
        recent_expenses = Expense.objects.filter(user=user).select_related('category')[:5]

        transactions = []
        for inc in recent_incomes:
            transactions.append({
                'date': inc.date,
                'created_at': inc.created_at,
                'type': 'Income',
                'amount': inc.amount,
                'category_or_source': inc.source,
                'description': inc.description,
            })
        for exp in recent_expenses:
            transactions.append({
                'date': exp.date,
                'created_at': exp.created_at,
                'type': 'Expense',
                'amount': exp.amount,
                'category_or_source': exp.category.name if exp.category else 'Uncategorized',
                'description': exp.description,
            })

        # Sort transactions: newest date first, then newest creation time first
        transactions.sort(key=lambda x: (x['date'], x['created_at']), reverse=True)
        recent_transactions = transactions[:5]

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
        })

        # Forms (if not already added in post)
        if 'income_form' not in context:
            context['income_form'] = DashboardIncomeForm()
        if 'expense_form' not in context:
            context['expense_form'] = DashboardExpenseForm(user=user)

        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        user = request.user
        today = timezone.localdate()

        if action == 'add_income':
            income_form = DashboardIncomeForm(request.POST)
            if income_form.is_valid():
                income = income_form.save(commit=False)
                income.user = user
                income.date = today
                income.save()
                messages.success(request, "Income record added successfully!")
                return redirect('dashboard')
            else:
                messages.error(request, "Please correct the errors in the Quick Add Income form.")
                # Return the invalid form to display errors
                return self.render_to_response(self.get_context_data(
                    income_form=income_form,
                    expense_form=DashboardExpenseForm(user=user)
                ))

        elif action == 'add_expense':
            expense_form = DashboardExpenseForm(request.POST, user=user)
            if expense_form.is_valid():
                expense = expense_form.save(commit=False)
                expense.user = user
                expense.date = today
                expense.save()
                messages.success(request, "Expense record added successfully!")
                return redirect('dashboard')
            else:
                messages.error(request, "Please correct the errors in the Quick Add Expense form.")
                # Return the invalid form to display errors
                return self.render_to_response(self.get_context_data(
                    income_form=DashboardIncomeForm(),
                    expense_form=expense_form
                ))

        return redirect('dashboard')
