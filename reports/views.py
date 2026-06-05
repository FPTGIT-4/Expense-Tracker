from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
import datetime
from .services import ReportDataService

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
            if start_str and end_str:
                try:
                    start_date = datetime.datetime.strptime(start_str, '%Y-%m-%d').date()
                    end_date = datetime.datetime.strptime(end_str, '%Y-%m-%d').date()
                except ValueError:
                    start_date = today.replace(day=1)
                    end_date = today
                    filter_type = 'this_month'
            else:
                start_date = today.replace(day=1)
                end_date = today
                filter_type = 'this_month'
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
