from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.db.models import Sum, Count, Q
from decimal import Decimal
import datetime
import json

from income.models import Income
from expenses.models import Expense
from budgets.models import Budget
from goals.models import Goal
from debts.models import Debt
from accounts.models import Account
from companies.models import CompanyAccount, CompanyIncome, CompanyExpense

class AnalyticsDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'analytics/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = timezone.localdate()

        # Resolve date filter
        date_filter = self.request.GET.get('date_filter', 'this_month')
        start_date = None
        end_date = None

        if date_filter == 'today':
            start_date = today
            end_date = today
        elif date_filter == 'this_week':
            start_date = today - datetime.timedelta(days=today.weekday())
            end_date = start_date + datetime.timedelta(days=6)
        elif date_filter == 'this_month':
            start_date = today.replace(day=1)
            next_month = today.replace(day=28) + datetime.timedelta(days=4)
            end_date = next_month - datetime.timedelta(days=next_month.day)
        elif date_filter == 'this_year':
            start_date = today.replace(month=1, day=1)
            end_date = today.replace(month=12, day=31)
        elif date_filter == 'custom':
            start_str = self.request.GET.get('start_date')
            end_str = self.request.GET.get('end_date')
            try:
                if start_str:
                    start_date = datetime.datetime.strptime(start_str, '%Y-%m-%d').date()
                else:
                    start_date = today.replace(day=1)
                
                if end_str:
                    end_date = datetime.datetime.strptime(end_str, '%Y-%m-%d').date()
                else:
                    end_date = today
            except ValueError:
                start_date = today.replace(day=1)
                end_date = today
        else:
            date_filter = 'this_month'
            start_date = today.replace(day=1)
            next_month = today.replace(day=28) + datetime.timedelta(days=4)
            end_date = next_month - datetime.timedelta(days=next_month.day)

        # ── 1. Query Sets filtered by range ─────────────────────────────────────
        personal_income_qs = Income.objects.filter(user=user, date__range=(start_date, end_date))
        personal_expense_qs = Expense.objects.filter(user=user, date__range=(start_date, end_date))
        company_income_qs = CompanyIncome.objects.filter(company_account__user=user, date__range=(start_date, end_date))
        company_expense_qs = CompanyExpense.objects.filter(company_account__user=user, date__range=(start_date, end_date))

        # Sum values
        personal_income_sum = personal_income_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        personal_expense_sum = personal_expense_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        company_income_sum = company_income_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        company_expense_sum = company_expense_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        total_income = personal_income_sum + company_income_sum
        total_expenses = personal_expense_sum + company_expense_sum
        net_savings = total_income - total_expenses
        personal_net_savings = personal_income_sum - personal_expense_sum
        company_net = company_income_sum - company_expense_sum

        # ── 2. Budget Calculations ──────────────────────────────────────────────
        # Find distinct months that fall within range
        months_in_range = []
        curr = start_date
        while curr <= end_date:
            pair = (curr.month, curr.year)
            if pair not in months_in_range:
                months_in_range.append(pair)
            if curr.month == 12:
                curr = curr.replace(year=curr.year + 1, month=1, day=1)
            else:
                curr = curr.replace(month=curr.month + 1, day=1)

        budget_q = Q()
        for m, y in months_in_range:
            budget_q |= Q(month=m, year=y)
        
        budgets_qs = Budget.objects.filter(user=user, is_active=True).filter(budget_q) if months_in_range else Budget.objects.none()
        total_budget_amount = budgets_qs.aggregate(total=Sum('budget_amount'))['total'] or Decimal('0.00')
        total_budget_spent = sum((b.total_spent for b in budgets_qs), Decimal('0.00'))
        budget_usage_pct = float((total_budget_spent / total_budget_amount) * 100) if total_budget_amount > 0 else 0.0

        # ── 3. Goals Progress ──────────────────────────────────────────────────
        goals_qs = Goal.objects.filter(user=user)
        total_goals_target = goals_qs.aggregate(total=Sum('target_amount'))['total'] or Decimal('0.00')
        total_goals_current = goals_qs.aggregate(total=Sum('current_amount'))['total'] or Decimal('0.00')
        goals_progress_pct = float((total_goals_current / total_goals_target) * 100) if total_goals_target > 0 else 0.0

        # ── 4. Active Debts Summary ─────────────────────────────────────────────
        active_debts = Debt.objects.filter(user=user, status='Active')
        total_borrowed_remaining = sum((d.remaining_balance for d in active_debts if d.debt_type == 'Borrowed'), Decimal('0.00'))
        total_lent_remaining = sum((d.remaining_balance for d in active_debts if d.debt_type == 'Lent'), Decimal('0.00'))
        net_debt_exposure = total_lent_remaining - total_borrowed_remaining

        # ── 5. Company Account Performance ──────────────────────────────────────
        company_accounts = CompanyAccount.objects.filter(user=user)
        company_perf = []
        for co in company_accounts:
            co_income = CompanyIncome.objects.filter(company_account=co, date__range=(start_date, end_date)).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            co_expense = CompanyExpense.objects.filter(company_account=co, date__range=(start_date, end_date)).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            company_perf.append({
                'account': co,
                'current_balance': co.current_balance,
                'income_in_range': co_income,
                'expense_in_range': co_expense,
                'net_in_range': co_income - co_expense,
            })

        # ── 6. Analytics Cards calculations ─────────────────────────────────────
        # Top Spending Category
        top_category_data = personal_expense_qs.values('category__name').annotate(total=Sum('amount')).order_by('-total').first()
        if top_category_data:
            top_spending_category = top_category_data['category__name'] or 'Uncategorized'
            top_spending_amount = top_category_data['total']
        else:
            top_spending_category = 'None'
            top_spending_amount = Decimal('0.00')

        # Highest Expense
        highest_personal_expense = personal_expense_qs.order_by('-amount').first()
        highest_company_expense = company_expense_qs.order_by('-amount').first()
        highest_expense_name = 'None'
        highest_expense_amount = Decimal('0.00')

        if highest_personal_expense and highest_company_expense:
            if highest_personal_expense.amount >= highest_company_expense.amount:
                highest_expense_name = highest_personal_expense.name
                highest_expense_amount = highest_personal_expense.amount
            else:
                highest_expense_name = f"[Co] {highest_company_expense.name}"
                highest_expense_amount = highest_company_expense.amount
        elif highest_personal_expense:
            highest_expense_name = highest_personal_expense.name
            highest_expense_amount = highest_personal_expense.amount
        elif highest_company_expense:
            highest_expense_name = f"[Co] {highest_company_expense.name}"
            highest_expense_amount = highest_company_expense.amount

        # Highest Income
        highest_personal_income = personal_income_qs.order_by('-amount').first()
        highest_company_income = company_income_qs.order_by('-amount').first()
        highest_income_source = 'None'
        highest_income_amount = Decimal('0.00')

        if highest_personal_income and highest_company_income:
            if highest_personal_income.amount >= highest_company_income.amount:
                highest_income_source = highest_personal_income.source
                highest_income_amount = highest_personal_income.amount
            else:
                highest_income_source = f"[Co] {highest_company_income.source}"
                highest_income_amount = highest_company_income.amount
        elif highest_personal_income:
            highest_income_source = highest_personal_income.source
            highest_income_amount = highest_personal_income.amount
        elif highest_company_income:
            highest_income_source = f"[Co] {highest_company_income.source}"
            highest_income_amount = highest_company_income.amount

        # Best Saving Month
        best_month_name = 'None'
        best_month_savings = Decimal('0.00')
        best_month_net = Decimal('-999999999.00')
        import calendar
        for m in range(1, 13):
            m_personal_inc = Income.objects.filter(user=user, date__year=today.year, date__month=m).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            m_company_inc = CompanyIncome.objects.filter(company_account__user=user, date__year=today.year, date__month=m).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            m_personal_exp = Expense.objects.filter(user=user, date__year=today.year, date__month=m).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            m_company_exp = CompanyExpense.objects.filter(company_account__user=user, date__year=today.year, date__month=m).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            m_savings = (m_personal_inc + m_company_inc) - (m_personal_exp + m_company_exp)
            if m_savings > 0 and m_savings > best_month_net:
                best_month_net = m_savings
                best_month_savings = m_savings
                best_month_name = calendar.month_name[m]

        # Current Month Summary
        current_month_personal_inc = Income.objects.filter(user=user, date__year=today.year, date__month=today.month).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        current_month_company_inc = CompanyIncome.objects.filter(company_account__user=user, date__year=today.year, date__month=today.month).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        current_month_personal_exp = Expense.objects.filter(user=user, date__year=today.year, date__month=today.month).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        current_month_company_exp = CompanyExpense.objects.filter(company_account__user=user, date__year=today.year, date__month=today.month).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        current_month_income = current_month_personal_inc + current_month_company_inc
        current_month_expenses = current_month_personal_exp + current_month_company_exp
        current_month_savings = current_month_income - current_month_expenses

        # Total Transactions
        total_transactions_count = (
            personal_income_qs.count() +
            personal_expense_qs.count() +
            company_income_qs.count() +
            company_expense_qs.count()
        )

        # ── 7. Charts Serialization ─────────────────────────────────────────────
        # 1. Income vs Expense
        income_vs_expense_data = {
            'categories': ["Personal", "Company/Business"],
            'income': [float(personal_income_sum), float(company_income_sum)],
            'expense': [float(personal_expense_sum), float(company_expense_sum)]
        }

        # 2. Monthly Trend (Income vs Expense)
        monthly_trend_data = {
            'categories': ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
            'income': [float(
                (Income.objects.filter(user=user, date__year=today.year, date__month=m).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')) +
                (CompanyIncome.objects.filter(company_account__user=user, date__year=today.year, date__month=m).aggregate(total=Sum('amount'))['total'] or Decimal('0.00'))
            ) for m in range(1, 13)],
            'expense': [float(
                (Expense.objects.filter(user=user, date__year=today.year, date__month=m).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')) +
                (CompanyExpense.objects.filter(company_account__user=user, date__year=today.year, date__month=m).aggregate(total=Sum('amount'))['total'] or Decimal('0.00'))
            ) for m in range(1, 13)]
        }

        # 3. Category distribution (Doughnut)
        personal_cats = personal_expense_qs.values('category__name').annotate(total=Sum('amount')).order_by('-total')
        company_cats = company_expense_qs.values('category__name').annotate(total=Sum('amount')).order_by('-total')
        
        cat_totals = {}
        for item in personal_cats:
            name = item['category__name'] or 'Uncategorized'
            cat_totals[name] = cat_totals.get(name, Decimal('0.00')) + item['total']
        for item in company_cats:
            name = item['category__name'] or 'Uncategorized'
            cat_totals[name] = cat_totals.get(name, Decimal('0.00')) + item['total']
            
        sorted_cats = sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)
        category_distribution_data = {
            'labels': [name for name, total in sorted_cats],
            'series': [float(total) for name, total in sorted_cats]
        }

        # 4. Budget Utilization
        current_month_budgets = Budget.objects.filter(user=user, is_active=True, month=today.month, year=today.year)
        budget_categories = []
        budget_allocated = []
        budget_spent = []
        for b in current_month_budgets:
            budget_categories.append(b.category.name)
            budget_allocated.append(float(b.budget_amount))
            budget_spent.append(float(b.total_spent))
            
        budget_utilization_data = {
            'categories': budget_categories,
            'allocated': budget_allocated,
            'spent': budget_spent
        }

        # Currency symbol
        try:
            currency_symbol = user.settings.currency
        except Exception:
            currency_symbol = '₹'

        context.update({
            # Date Filter
            'date_filter': date_filter,
            'start_date_val': start_date.strftime('%Y-%m-%d') if start_date else '',
            'end_date_val': end_date.strftime('%Y-%m-%d') if end_date else '',
            'start_date': start_date,
            'end_date': end_date,
            
            # Financial KPIs
            'currency_symbol': currency_symbol,
            'total_income': total_income,
            'total_expenses': total_expenses,
            'net_savings': net_savings,
            'personal_income_sum': personal_income_sum,
            'personal_expense_sum': personal_expense_sum,
            'personal_net_savings': personal_net_savings,
            'company_income_sum': company_income_sum,
            'company_expense_sum': company_expense_sum,
            'company_net': company_net,
            
            # Budget & Goals
            'total_budget_amount': total_budget_amount,
            'total_budget_spent': total_budget_spent,
            'budget_usage_pct': budget_usage_pct,
            'goals_progress_pct': goals_progress_pct,
            'total_goals_target': total_goals_target,
            'total_goals_current': total_goals_current,
            
            # Debts
            'total_borrowed_remaining': total_borrowed_remaining,
            'total_lent_remaining': total_lent_remaining,
            'net_debt_exposure': net_debt_exposure,
            
            # Company accounts
            'company_perf': company_perf,
            
            # Cards
            'top_spending_category': top_spending_category,
            'top_spending_amount': top_spending_amount,
            'highest_expense_name': highest_expense_name,
            'highest_expense_amount': highest_expense_amount,
            'highest_income_source': highest_income_source,
            'highest_income_amount': highest_income_amount,
            'best_month_name': best_month_name,
            'best_month_savings': best_month_savings,
            'current_month_income': current_month_income,
            'current_month_expenses': current_month_expenses,
            'current_month_savings': current_month_savings,
            'total_transactions_count': total_transactions_count,
            'current_year': today.year,

            # Charts data serialized
            'chart_inc_vs_exp': json.dumps(income_vs_expense_data),
            'chart_monthly_trend': json.dumps(monthly_trend_data),
            'chart_category_dist': json.dumps(category_distribution_data),
            'chart_budget_util': json.dumps(budget_utilization_data),
        })
        return context
