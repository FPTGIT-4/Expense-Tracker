from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.db.models import Sum
import datetime
from decimal import Decimal
from .services import ReportDataService
from accounts.models import Account
from income.models import Income
from expenses.models import Expense

class ReportsDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'reports/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = timezone.localdate()

        filter_type = self.request.GET.get('date_filter', 'this_month')
        start_date = None
        end_date = None

        if filter_type == 'today':
            start_date = today
            end_date = today
        elif filter_type == 'this_week':
            start_date = today - datetime.timedelta(days=today.weekday())
            end_date = today
        elif filter_type == 'this_month':
            start_date = today.replace(day=1)
            end_date = today
        elif filter_type == 'this_year':
            start_date = today.replace(month=1, day=1)
            end_date = today
        elif filter_type == 'custom':
            start_str = self.request.GET.get('start_date')
            end_str = self.request.GET.get('end_date')
            try:
                if start_str:
                    start_date = datetime.datetime.strptime(start_str, '%Y-%m-%d').date()
                else:
                    start_date = today
                
                if end_str:
                    end_date = datetime.datetime.strptime(end_str, '%Y-%m-%d').date()
                else:
                    end_date = today
            except ValueError:
                start_date = today
                end_date = today
        else:
            start_date = today.replace(day=1)
            end_date = today
            filter_type = 'this_month'

        # Fetch report figures from service layer
        report_data = ReportDataService.get_report_data(user, start_date, end_date)

        context.update(report_data)
        context.update({
            'date_filter': filter_type,
            'start_date_val': start_date.strftime('%Y-%m-%d') if start_date else '',
            'end_date_val': end_date.strftime('%Y-%m-%d') if end_date else '',
            'start_date': start_date,
            'end_date': end_date,
            'today': today,
        })
        return context


def _resolve_date_range(request, today):
    """Helper shared by account report views to resolve date filter params."""
    filter_type = request.GET.get('date_filter', 'this_month')
    start_date = end_date = None

    if filter_type == 'today':
        start_date = end_date = today
    elif filter_type == 'this_week':
        start_date = today - datetime.timedelta(days=today.weekday())
        end_date = today
    elif filter_type == 'this_month':
        start_date = today.replace(day=1)
        end_date = today
    elif filter_type == 'this_year':
        start_date = today.replace(month=1, day=1)
        end_date = today
    elif filter_type == 'custom':
        start_str = request.GET.get('start_date')
        end_str = request.GET.get('end_date')
        try:
            if start_str:
                start_date = datetime.datetime.strptime(start_str, '%Y-%m-%d').date()
            else:
                start_date = today
            
            if end_str:
                end_date = datetime.datetime.strptime(end_str, '%Y-%m-%d').date()
            else:
                end_date = today
        except ValueError:
            start_date = today
            end_date = today
    else:
        filter_type = 'this_month'
        start_date = today.replace(day=1)
        end_date = today

    return filter_type, start_date, end_date


class AccountReportsView(LoginRequiredMixin, TemplateView):
    """Per-account income/expense/net report with date-range filtering."""
    template_name = 'reports/account_reports.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = timezone.localdate()

        filter_type, start_date, end_date = _resolve_date_range(self.request, today)

        # All user accounts
        accounts = Account.objects.filter(user=user).order_by('name')

        # Overall totals in the selected period
        total_income = Income.objects.filter(
            user=user, date__range=(start_date, end_date)
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        total_expense = Expense.objects.filter(
            user=user, date__range=(start_date, end_date)
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        net_change = total_income - total_expense

        # Per-account breakdown
        account_summary = []
        for acc in accounts:
            acc_income = Income.objects.filter(
                user=user, account=acc, date__range=(start_date, end_date)
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            acc_expense = Expense.objects.filter(
                user=user, account=acc, date__range=(start_date, end_date)
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            acc_net = acc_income - acc_expense

            account_summary.append({
                'account': acc,
                'income': acc_income,
                'expense': acc_expense,
                'net': acc_net,
                'current_balance': acc.current_balance,
            })

        # Sort by absolute net change descending (most active first)
        account_summary.sort(key=lambda x: abs(x['net']), reverse=True)

        context.update({
            'date_filter': filter_type,
            'start_date': start_date,
            'end_date': end_date,
            'start_date_val': start_date.strftime('%Y-%m-%d') if start_date else '',
            'end_date_val': end_date.strftime('%Y-%m-%d') if end_date else '',
            'today': today,
            'total_income': total_income,
            'total_expense': total_expense,
            'net_change': net_change,
            'account_summary': account_summary,
            'total_accounts': accounts.count(),
        })
        return context
