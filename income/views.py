import json
from decimal import Decimal
from django.shortcuts import render
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
import datetime

from .models import Income
from .forms import IncomeForm
from config.utils import get_analytics_date_range


class IncomeListView(LoginRequiredMixin, ListView):
    model = Income
    template_name = 'income/income_list.html'
    context_object_name = 'incomes'
    paginate_by = 15

    def get_queryset(self):
        qs = Income.objects.filter(user=self.request.user)
        
        # Keep only Today, This Week, and This Month filters
        date_filter = self.request.GET.get('date_filter', 'this_month').strip().lower()
        if date_filter not in ['today', 'this_week', 'this_month']:
            # Force default to this_month if anything else (like custom) is passed
            date_filter = 'this_month'
            
        start_date, end_date, _ = get_analytics_date_range(self.request)
        qs = qs.filter(date__range=(start_date, end_date))
        return qs.order_by('-date', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        start_date, end_date, date_filter = get_analytics_date_range(self.request)
        if date_filter not in ['today', 'this_week', 'this_month']:
            date_filter = 'this_month'

        queryset = self.get_queryset()
        total_income = queryset.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        context.update({
            'start_date': start_date,
            'end_date': end_date,
            'date_filter': date_filter,
            'total_income': total_income,
        })
        return context


class IncomeCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Income
    form_class = IncomeForm
    template_name = 'income/income_form.html'
    success_url = reverse_lazy('income-list')
    success_message = "Income record created successfully!"

    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)

        post_data = self.request.POST
        row_indices_str = post_data.get('new_row_indices', '')
        if row_indices_str:
            from decimal import Decimal
            indices = [int(idx) for idx in row_indices_str.split(',') if idx.strip()]
            for idx in indices:
                amount_str = post_data.get(f'amount_new_{idx}', '').strip()
                category_id = post_data.get(f'category_new_{idx}', '').strip()
                desc = post_data.get(f'description_new_{idx}', '').strip()

                if amount_str and category_id:
                    try:
                        amount = Decimal(amount_str)
                        date = form.cleaned_data.get('date')
                        account = form.cleaned_data.get('account')
                        Income.objects.create(
                            user=self.request.user,
                            account=account,
                            amount=amount,
                            category_id=int(category_id),
                            date=date,
                            description=desc if desc else None
                        )
                    except Exception:
                        pass
        return response

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class IncomeUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Income
    form_class = IncomeForm
    template_name = 'income/income_form.html'
    success_url = reverse_lazy('income-list')
    success_message = "Income record updated successfully!"

    def get_queryset(self):
        return Income.objects.filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)

        post_data = self.request.POST
        row_indices_str = post_data.get('new_row_indices', '')
        if row_indices_str:
            from decimal import Decimal
            indices = [int(idx) for idx in row_indices_str.split(',') if idx.strip()]
            for idx in indices:
                amount_str = post_data.get(f'amount_new_{idx}', '').strip()
                category_id = post_data.get(f'category_new_{idx}', '').strip()
                desc = post_data.get(f'description_new_{idx}', '').strip()

                if amount_str and category_id:
                    try:
                        amount = Decimal(amount_str)
                        date = form.cleaned_data.get('date')
                        account = form.cleaned_data.get('account')
                        Income.objects.create(
                            user=self.request.user,
                            account=account,
                            amount=amount,
                            category_id=int(category_id),
                            date=date,
                            description=desc if desc else None
                        )
                    except Exception:
                        pass
        return response


class IncomeDeleteView(LoginRequiredMixin, DeleteView):
    model = Income
    template_name = 'income/income_confirm_delete.html'
    success_url = reverse_lazy('income-list')

    def get_queryset(self):
        return Income.objects.filter(user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Income record deleted successfully!")
        return super().form_valid(form)
