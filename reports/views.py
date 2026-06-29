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
        if filter_type not in ['today', 'this_week', 'this_month', 'this_year']:
            filter_type = 'this_month'

        if filter_type == 'today':
            start_date = today
            end_date = today
        elif filter_type == 'this_week':
            start_date = today - datetime.timedelta(days=today.weekday())
            end_date = start_date + datetime.timedelta(days=6)
        elif filter_type == 'this_month':
            start_date = today.replace(day=1)
            end_date = today
        elif filter_type == 'this_year':
            start_date = today.replace(month=1, day=1)
            end_date = today

        # Fetch report figures from service layer
        report_data = ReportDataService.get_report_data(user, start_date, end_date)

        context.update(report_data)
        context.update({
            'date_filter': filter_type,
            'start_date': start_date,
            'end_date': end_date,
            'today': today,
        })
        return context
