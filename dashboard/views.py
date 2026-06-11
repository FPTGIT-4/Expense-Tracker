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
from accounts.models import Account, AccountTransfer

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
        
        accounts = Account.objects.filter(user=user).order_by('name')
        total_balance = sum(acc.current_balance for acc in accounts)
        total_categories = Category.objects.filter(user=user).count()
        # accounts_below_minimum is provided by the context processor (global_accounts_below_minimum)
        # expose it as accounts_below_minimum for template backward-compat

        # --- Account Intelligence ---
        active_accounts = [acc for acc in accounts if acc.status != 'CLOSED']

        # Highest and Lowest balance among active accounts
        highest_balance_account = max(active_accounts, key=lambda a: a.current_balance) if active_accounts else None
        lowest_balance_account  = min(active_accounts, key=lambda a: a.current_balance) if active_accounts else None

        # Balance grouped by type
        total_cash_balance = sum(
            acc.current_balance for acc in accounts
            if acc.account_type == 'Cash' and acc.status != 'CLOSED'
        )
        total_bank_balance = sum(
            acc.current_balance for acc in accounts
            if acc.account_type == 'Bank Account' and acc.status != 'CLOSED'
        )

        # Transfer statistics (all-time for user)
        user_transfers = AccountTransfer.objects.filter(user=user)
        transfer_count = user_transfers.count()
        transfer_total = user_transfers.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # This month transfers
        start_of_month = today.replace(day=1)
        transfer_count_month = user_transfers.filter(transfer_date__gte=start_of_month).count()
        transfer_total_month  = user_transfers.filter(transfer_date__gte=start_of_month).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')

        transfer_stats = {
            'count':        transfer_count,
            'total':        transfer_total,
            'count_month':  transfer_count_month,
            'total_month':  transfer_total_month,
        }

        # Today's statistics
        income_today = Income.objects.filter(user=user, date=today).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        expenses_today = Expense.objects.filter(user=user, date=today).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        savings_today = income_today - expenses_today
        count_today = Income.objects.filter(user=user, date=today).count() + Expense.objects.filter(user=user, date=today).count()

        # Helper for period statistics
        def get_period_stats(start_date, is_today=False):
            if is_today:
                inc_qs = Income.objects.filter(user=user, date=today)
                exp_qs = Expense.objects.filter(user=user, date=today)
            else:
                inc_qs = Income.objects.filter(user=user, date__gte=start_date)
                exp_qs = Expense.objects.filter(user=user, date__gte=start_date)
            
            inc_total = inc_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            exp_total = exp_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            return {
                'income': float(inc_total),
                'expense': float(exp_total),
                'savings': float(inc_total - exp_total),
                'count': inc_qs.count() + exp_qs.count(),
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': today.strftime('%Y-%m-%d')
            }

        start_of_week = today - timedelta(days=today.weekday())
        start_of_month = today.replace(day=1)
        start_of_year = today.replace(month=1, day=1)

        financial_summary = {
            'today': get_period_stats(today, is_today=True),
            'week': get_period_stats(start_of_week),
            'month': get_period_stats(start_of_month),
            'year': get_period_stats(start_of_year)
        }

        # Recent transactions (fetch up to 20 for each type, sorted)
        db_incomes = Income.objects.filter(user=user).prefetch_related('labels').order_by('-date', '-created_at')[:20]
        db_expenses = Expense.objects.filter(user=user).select_related('category').prefetch_related('labels').order_by('-date', '-created_at')[:20]

        recent_incomes = []
        for inc in db_incomes:
            recent_incomes.append({
                'date': inc.date,
                'created_at': inc.created_at,
                'type': 'Income',
                'amount': inc.amount,
                'category_or_source': inc.source,
                'description': inc.description,
                'labels': list(inc.labels.all()),
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
                'labels': list(exp.labels.all()),
            })

        # Combined transactions
        all_transactions = recent_incomes + recent_expenses
        all_transactions.sort(key=lambda x: (x['date'], x['created_at']), reverse=True)
        recent_transactions = all_transactions[:20]

        # Context variables
        context.update({
            'today': today,
            'total_income': total_income,
            'total_expenses': total_expenses,
            'total_balance': total_balance,
            'current_balance': total_balance,
            'accounts': accounts,
            'total_categories': total_categories,
            'income_today': income_today,
            'expenses_today': expenses_today,
            'savings_today': savings_today,
            'count_today': count_today,
            'financial_summary': financial_summary,
            'recent_transactions': recent_transactions,
            'recent_incomes': recent_incomes,
            'recent_expenses': recent_expenses,
            'source_choices': Income.SOURCE_CHOICES,
            'categories': Category.objects.filter(user=user).order_by('name'),
            # accounts_below_minimum provided by context processor as global_accounts_below_minimum
            # Account Intelligence
            'highest_balance_account': highest_balance_account,
            'lowest_balance_account':  lowest_balance_account,
            'total_cash_balance':      total_cash_balance,
            'total_bank_balance':      total_bank_balance,
            'transfer_stats':          transfer_stats,
        })

        return context

    def post(self, request, *args, **kwargs):
        return redirect('dashboard')
