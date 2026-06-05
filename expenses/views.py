from django.shortcuts import render
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.db.models import Q, Sum
import datetime

from .models import Expense
from .forms import ExpenseForm
from categories.models import Category


import json
from decimal import Decimal
from django.shortcuts import render
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.db.models import Q, Sum, Count
import datetime

from .models import Expense
from .forms import ExpenseForm
from categories.models import Category
from config.utils import get_analytics_date_range


class ExpenseListView(LoginRequiredMixin, ListView):
    model = Expense
    template_name = 'expenses/expense_list.html'
    context_object_name = 'expenses'
    paginate_by = 15

    def get_queryset(self):
        qs = Expense.objects.filter(user=self.request.user)
        params = self.request.GET

        # Search by name or description
        search = params.get('search', '').strip()
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))

        # Category filter
        category = params.get('category', '').strip()
        if category:
            if category == '__none__':
                qs = qs.filter(category__isnull=True)
            else:
                try:
                    qs = qs.filter(category_id=int(category))
                except ValueError:
                    pass

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
        elif sort_by == 'name_asc':
            qs = qs.order_by('name', '-date', '-created_at')
        elif sort_by == 'name_desc':
            qs = qs.order_by('-name', '-date', '-created_at')
        elif sort_by == 'category_asc':
            qs = qs.order_by('category__name', '-date', '-created_at')
        elif sort_by == 'category_desc':
            qs = qs.order_by('-category__name', '-date', '-created_at')
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
        analytics_qs = Expense.objects.filter(user=user, date__range=(start_date, end_date))

        # 1. Summary Card Calculations
        total_expense = analytics_qs.aggregate(t=Sum('amount'))['t'] or Decimal('0.00')
        total_count = analytics_qs.count()

        highest_cat_data = analytics_qs.values('category__name') \
                                       .annotate(total=Sum('amount')) \
                                       .order_by('-total') \
                                       .first()
        highest_category = highest_cat_data if highest_cat_data else None

        # 2. Category spending breakdown list (including Uncategorized)
        annotated_cats = Category.objects.filter(user=user).annotate(
            total_spent=Sum('expenses__amount', filter=Q(expenses__date__range=(start_date, end_date))),
            txn_count=Count('expenses', filter=Q(expenses__date__range=(start_date, end_date)))
        ).order_by('-total_spent')

        # Uncategorized expenses
        uncategorized_data = analytics_qs.filter(category__isnull=True).aggregate(
            total=Sum('amount'),
            count=Count('id')
        )
        uncat_spent = uncategorized_data['total'] or Decimal('0.00')
        uncat_count = uncategorized_data['count'] or 0

        categories_data = []
        for cat in annotated_cats:
            spent = cat.total_spent or Decimal('0.00')
            if spent > 0:
                pct = (spent / total_expense * 100) if total_expense > 0 else 0
                categories_data.append({
                    'name': cat.name,
                    'total_spent': spent,
                    'txn_count': cat.txn_count,
                    'percentage': pct
                })
        
        if uncat_spent > 0:
            pct = (uncat_spent / total_expense * 100) if total_expense > 0 else 0
            categories_data.append({
                'name': 'Uncategorized',
                'total_spent': uncat_spent,
                'txn_count': uncat_count,
                'percentage': pct
            })

        # Sort breakdown by total spent descending
        categories_data.sort(key=lambda x: x['total_spent'], reverse=True)

        # 3. Chart data serialization
        # Pie Chart: Expense by Category
        pie_chart_data = {
            'labels': [c['name'] for c in categories_data],
            'data': [float(c['total_spent']) for c in categories_data]
        }

        # Line Chart: Expense Trend Over Time
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
            'total_expense': total_expense,
            'total_count': total_count,
            'highest_category': highest_category,
            'categories_data': categories_data,
            'start_date': start_date,
            'end_date': end_date,
            'date_filter': date_filter,
            'category_chart_json': json.dumps(pie_chart_data),
            'trend_chart_json': json.dumps(trend_chart_data),
            
            # Pass filter values back to template for persistence
            'search': params.get('search', ''),
            'category_id': params.get('category', ''),
            'date_from': start_date.strftime('%Y-%m-%d'),
            'date_to': end_date.strftime('%Y-%m-%d'),
            'amount_min': params.get('amount_min', ''),
            'amount_max': params.get('amount_max', ''),
            'categories': Category.objects.filter(user=user).order_by('name'),
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
        if context['category_id']:
            if context['category_id'] == '__none__':
                filters.append('Category: Uncategorized')
            else:
                try:
                    cat = Category.objects.get(pk=int(context['category_id']), user=user)
                    filters.append(f'Category: {cat.name}')
                except (Category.DoesNotExist, ValueError):
                    pass
        if date_filter != 'this_month' or context['amount_min'] or context['amount_max']:
            filters.append(f'Time filter: {date_filter.replace("_", " ").title()}')
        if context['amount_min'] or context['amount_max']:
            amt = f'&#8377;{context["amount_min"] or "0"} – &#8377;{context["amount_max"] or "any"}'
            filters.append(f'Amount: {amt}')
        context['active_filters'] = filters
        context['has_filters'] = bool(filters)

        return context


class ExpenseCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Expense
    form_class = ExpenseForm
    template_name = 'expenses/expense_form.html'
    success_url = reverse_lazy('expense-list')
    success_message = "Expense record created successfully!"

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class ExpenseUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Expense
    form_class = ExpenseForm
    template_name = 'expenses/expense_form.html'
    success_url = reverse_lazy('expense-list')
    success_message = "Expense record updated successfully!"

    def get_queryset(self):
        return Expense.objects.filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class ExpenseDeleteView(LoginRequiredMixin, DeleteView):
    model = Expense
    template_name = 'expenses/expense_confirm_delete.html'
    success_url = reverse_lazy('expense-list')

    def get_queryset(self):
        return Expense.objects.filter(user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Expense record deleted successfully!")
        return super().form_valid(form)
