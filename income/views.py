from django.shortcuts import render
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.core.paginator import Paginator
from django.db.models import Q, Sum
import datetime

from .models import Income
from .forms import IncomeForm


class IncomeListView(LoginRequiredMixin, ListView):
    model = Income
    template_name = 'income/income_list.html'
    context_object_name = 'incomes'
    paginate_by = 15

    def get_queryset(self):
        qs = Income.objects.filter(user=self.request.user).order_by('-date', '-created_at')
        params = self.request.GET

        # Search by description
        search = params.get('search', '').strip()
        if search:
            qs = qs.filter(description__icontains=search)

        # Source filter (acts like category for income)
        source = params.get('source', '').strip()
        if source:
            qs = qs.filter(source=source)

        # Date range
        date_from = params.get('date_from', '').strip()
        date_to = params.get('date_to', '').strip()
        if date_from:
            try:
                qs = qs.filter(date__gte=datetime.datetime.strptime(date_from, '%Y-%m-%d').date())
            except ValueError:
                pass
        if date_to:
            try:
                qs = qs.filter(date__lte=datetime.datetime.strptime(date_to, '%Y-%m-%d').date())
            except ValueError:
                pass

        # Amount range
        amount_min = params.get('amount_min', '').strip()
        amount_max = params.get('amount_max', '').strip()
        if amount_min:
            try:
                qs = qs.filter(amount__gte=float(amount_min))
            except ValueError:
                pass
        if amount_max:
            try:
                qs = qs.filter(amount__lte=float(amount_max))
            except ValueError:
                pass

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filtered_qs = self.get_queryset()

        # Stats on filtered results
        context['total_income'] = filtered_qs.aggregate(t=Sum('amount'))['t'] or 0
        context['total_count'] = filtered_qs.count()

        # Pass filter values back to template for persistence
        params = self.request.GET
        context['search'] = params.get('search', '')
        context['source'] = params.get('source', '')
        context['date_from'] = params.get('date_from', '')
        context['date_to'] = params.get('date_to', '')
        context['amount_min'] = params.get('amount_min', '')
        context['amount_max'] = params.get('amount_max', '')

        # Source choices for dropdown
        context['source_choices'] = Income.SOURCE_CHOICES

        # Build query string without 'page' for pagination links
        query_params = params.copy()
        query_params.pop('page', None)
        context['query_string'] = query_params.urlencode()

        # Active filter summary
        filters = []
        if context['search']:
            filters.append(f'Search: "{context["search"]}"')
        if context['source']:
            filters.append(f'Source: {context["source"]}')
        if context['date_from'] or context['date_to']:
            date_range = f'{context["date_from"] or "start"} to {context["date_to"] or "today"}'
            filters.append(f'Date: {date_range}')
        if context['amount_min'] or context['amount_max']:
            amt = f'&#8377;{context["amount_min"] or "0"} – &#8377;{context["amount_max"] or "any"}'
            filters.append(f'Amount: {amt}')
        context['active_filters'] = filters
        context['has_filters'] = bool(filters)

        return context


class IncomeCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Income
    form_class = IncomeForm
    template_name = 'income/income_form.html'
    success_url = reverse_lazy('income-list')
    success_message = "Income record created successfully!"

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class IncomeUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Income
    form_class = IncomeForm
    template_name = 'income/income_form.html'
    success_url = reverse_lazy('income-list')
    success_message = "Income record updated successfully!"

    def get_queryset(self):
        return Income.objects.filter(user=self.request.user)


class IncomeDeleteView(LoginRequiredMixin, DeleteView):
    model = Income
    template_name = 'income/income_confirm_delete.html'
    success_url = reverse_lazy('income-list')

    def get_queryset(self):
        return Income.objects.filter(user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Income record deleted successfully!")
        return super().form_valid(form)
