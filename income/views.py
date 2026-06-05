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
        params = self.request.GET

        # Search by description
        search = params.get('search', '').strip()
        if search:
            qs = qs.filter(description__icontains=search)

        # Source filter
        source = params.get('source', '').strip()
        if source:
            qs = qs.filter(source=source)

        # Date range from analytics filter helper
        start_date, end_date, date_filter = get_analytics_date_range(self.request)
        qs = qs.filter(date__range=(start_date, end_date))

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

        # Sort order
        sort_by = params.get('sort_by', 'date_desc').strip().lower()
        if sort_by == 'date_asc':
            qs = qs.order_by('date', 'created_at')
        elif sort_by == 'amount_desc':
            qs = qs.order_by('-amount', '-date', '-created_at')
        elif sort_by == 'amount_asc':
            qs = qs.order_by('amount', 'date', 'created_at')
        elif sort_by == 'source_asc':
            qs = qs.order_by('source', '-date', '-created_at')
        elif sort_by == 'source_desc':
            qs = qs.order_by('-source', '-date', '-created_at')
        elif sort_by == 'description_asc':
            qs = qs.order_by('description', '-date', '-created_at')
        elif sort_by == 'description_desc':
            qs = qs.order_by('-description', '-date', '-created_at')
        else: # date_desc
            qs = qs.order_by('-date', '-created_at')

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        params = self.request.GET

        # Date range parsing
        start_date, end_date, date_filter = get_analytics_date_range(self.request)

        # Base analytics queryset (filtered only by user and selected date range)
        analytics_qs = Income.objects.filter(user=user, date__range=(start_date, end_date))

        # 1. Summary Card Calculations
        total_income = analytics_qs.aggregate(t=Sum('amount'))['t'] or Decimal('0.00')
        total_count = analytics_qs.count()

        largest_source_data = analytics_qs.values('source') \
                                          .annotate(total=Sum('amount')) \
                                          .order_by('-total') \
                                          .first()
        largest_source = largest_source_data if largest_source_data else None

        # 2. Source breakdown table analysis
        source_analysis = analytics_qs.values('source') \
                                      .annotate(total=Sum('amount'), count=Count('id')) \
                                      .order_by('-total')
        
        source_data = []
        for item in source_analysis:
            amt = item['total'] or Decimal('0.00')
            pct = (amt / total_income * 100) if total_income > 0 else 0
            source_data.append({
                'source': item['source'],
                'total_amount': amt,
                'txn_count': item['count'],
                'percentage': pct
            })

        # 3. Chart data serialization
        # Pie Chart: Income by Source
        pie_chart_data = {
            'labels': [s['source'] for s in source_data],
            'data': [float(s['total_amount']) for s in source_data]
        }

        # Line Chart: Income Trend Over Time
        trend_qs = analytics_qs.values('date') \
                               .annotate(total=Sum('amount')) \
                               .order_by('date')
        
        trend_chart_data = {
            'labels': [t['date'].strftime('%Y-%m-%d') for t in trend_qs],
            'data': [float(t['total']) for t in trend_qs]
        }

        # Filtered queryset stats for listing table header
        filtered_qs = self.get_queryset()
        context['list_total'] = filtered_qs.aggregate(t=Sum('amount'))['t'] or Decimal('0.00')
        context['list_count'] = filtered_qs.count()

        # Update context
        context.update({
            'total_income': total_income,
            'total_count': total_count,
            'largest_source': largest_source,
            'source_data': source_data,
            'start_date': start_date,
            'end_date': end_date,
            'date_filter': date_filter,
            'pie_chart_json': json.dumps(pie_chart_data),
            'trend_chart_json': json.dumps(trend_chart_data),
            
            # Pass filter values back to template for persistence
            'search': params.get('search', ''),
            'source': params.get('source', ''),
            'date_from': start_date.strftime('%Y-%m-%d'),
            'date_to': end_date.strftime('%Y-%m-%d'),
            'amount_min': params.get('amount_min', ''),
            'amount_max': params.get('amount_max', ''),
            'source_choices': Income.SOURCE_CHOICES,
            'sort_by': params.get('sort_by', 'date_desc').strip().lower(),
        })

        # Build query string without 'page' for pagination links
        query_params = params.copy()
        if 'date_filter' not in query_params:
            query_params['date_filter'] = date_filter
        if date_filter == 'custom':
            if 'date_from' not in query_params:
                query_params['date_from'] = start_date.strftime('%Y-%m-%d')
            if 'date_to' not in query_params:
                query_params['date_to'] = end_date.strftime('%Y-%m-%d')
        query_params.pop('page', None)
        context['query_string'] = query_params.urlencode()

        # Build query string without 'page' and 'sort_by' for sorting links
        sort_params = query_params.copy()
        sort_params.pop('sort_by', None)
        context['sort_query_string'] = sort_params.urlencode()

        # Active filter summary
        filters = []
        if context['search']:
            filters.append(f'Search: "{context["search"]}"')
        if context['source']:
            filters.append(f'Source: {context["source"]}')
        if date_filter != 'this_month' or context['amount_min'] or context['amount_max']:
            filters.append(f'Time filter: {date_filter.replace("_", " ").title()}')
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
