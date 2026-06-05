from decimal import Decimal
from django.shortcuts import render
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.db.models import Sum, Count, Q

from .models import Category
from .forms import CategoryForm
from expenses.models import Expense
from config.utils import get_analytics_date_range


class CategoryListView(LoginRequiredMixin, ListView):
    model = Category
    template_name = 'categories/category_list.html'
    context_object_name = 'categories'

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user).order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get active date range
        start_date, end_date, date_filter = get_analytics_date_range(self.request)
        
        # Total categories (lifetime management)
        total_categories = Category.objects.filter(user=user).count()
        
        # Total spent in date range across all categories
        total_spent = Expense.objects.filter(user=user, date__range=(start_date, end_date)) \
                                     .aggregate(t=Sum('amount'))['t'] or Decimal('0.00')
        
        # Annotated categories in date range
        annotated_cats = Category.objects.filter(user=user).annotate(
            total_spent=Sum('expenses__amount', filter=Q(expenses__date__range=(start_date, end_date))),
            txn_count=Count('expenses', filter=Q(expenses__date__range=(start_date, end_date)))
        ).order_by('name')
        
        # Uncategorized expenses in date range
        uncategorized_data = Expense.objects.filter(
            user=user, 
            category__isnull=True, 
            date__range=(start_date, end_date)
        ).aggregate(
            total=Sum('amount'),
            count=Count('id')
        )
        uncat_spent = uncategorized_data['total'] or Decimal('0.00')
        uncat_count = uncategorized_data['count'] or 0
        
        # Get active filters
        search = self.request.GET.get('search', '').strip()
        spent_min = self.request.GET.get('spent_min', '').strip()
        spent_max = self.request.GET.get('spent_max', '').strip()
        count_min = self.request.GET.get('count_min', '').strip()
        count_max = self.request.GET.get('count_max', '').strip()
        
        # Apply filters to annotated categories
        if search:
            annotated_cats = annotated_cats.filter(Q(name__icontains=search) | Q(description__icontains=search))
            
        if spent_min:
            try:
                annotated_cats = annotated_cats.filter(total_spent__gte=float(spent_min))
            except ValueError:
                pass
                
        if spent_max:
            try:
                annotated_cats = annotated_cats.filter(total_spent__lte=float(spent_max))
            except ValueError:
                pass
                
        if count_min:
            try:
                annotated_cats = annotated_cats.filter(txn_count__gte=int(count_min))
            except ValueError:
                pass
                
        if count_max:
            try:
                annotated_cats = annotated_cats.filter(txn_count__lte=int(count_max))
            except ValueError:
                pass

        # Determine if Uncategorized matches the filters
        uncat_matches = True
        if search:
            uncat_matches = ("uncategorized" in search.lower() or 
                             "expenses with no category assigned" in search.lower())
        if spent_min:
            try:
                if uncat_spent < float(spent_min):
                    uncat_matches = False
            except ValueError:
                pass
        if spent_max:
            try:
                if uncat_spent > float(spent_max):
                    uncat_matches = False
            except ValueError:
                pass
        if count_min:
            try:
                if uncat_count < int(count_min):
                    uncat_matches = False
            except ValueError:
                pass
        if count_max:
            try:
                if uncat_count > int(count_max):
                    uncat_matches = False
            except ValueError:
                pass

        # Build list with totals, counts, and percentages
        categories_data = []
        for cat in annotated_cats:
            spent = cat.total_spent or Decimal('0.00')
            pct = (spent / total_spent * 100) if total_spent > 0 else 0
            categories_data.append({
                'id': cat.pk,
                'name': cat.name,
                'description': cat.description,
                'created_at': cat.created_at,
                'total_spent': spent,
                'txn_count': cat.txn_count,
                'percentage': pct,
                'is_uncategorized': False
            })
            
        if uncat_spent > 0 and uncat_matches:
            pct = (uncat_spent / total_spent * 100) if total_spent > 0 else 0
            categories_data.append({
                'id': None,
                'name': 'Uncategorized',
                'description': 'Expenses with no category assigned',
                'created_at': None,
                'total_spent': uncat_spent,
                'txn_count': uncat_count,
                'percentage': pct,
                'is_uncategorized': True
            })
            
        # Calculate highest and lowest spending categories
        active_spendings = [c for c in categories_data if c['total_spent'] > 0]
        if active_spendings:
            # Sort descending to find highest/lowest
            active_spendings.sort(key=lambda x: x['total_spent'], reverse=True)
            highest_category = active_spendings[0]
            lowest_category = active_spendings[-1]
        else:
            highest_category = None
            lowest_category = None
            
        # Sort option
        sort_by = self.request.GET.get('sort_by', 'name_asc').strip().lower()
        if sort_by == 'name_desc':
            categories_data.sort(key=lambda x: x['name'].lower(), reverse=True)
        elif sort_by == 'spent_desc':
            categories_data.sort(key=lambda x: x['total_spent'], reverse=True)
        elif sort_by == 'spent_asc':
            categories_data.sort(key=lambda x: x['total_spent'])
        elif sort_by == 'count_desc':
            categories_data.sort(key=lambda x: x['txn_count'], reverse=True)
        elif sort_by == 'count_asc':
            categories_data.sort(key=lambda x: x['txn_count'])
        else: # name_asc default
            categories_data.sort(key=lambda x: x['name'].lower())
            
        # Build query string without 'page' for pagination links
        params = self.request.GET
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
        if search:
            filters.append(f'Search: "{search}"')
        if spent_min or spent_max:
            spent_str = f'&#8377;{spent_min or "0"} – &#8377;{spent_max or "any"}'
            filters.append(f'Spent: {spent_str}')
        if count_min or count_max:
            count_str = f'{count_min or "0"} – {count_max or "any"}'
            filters.append(f'Tx Count: {count_str}')
            
        context['active_filters'] = filters
        context['has_filters'] = bool(filters)

        # Pass variables to template context
        context.update({
            'total_categories': total_categories,
            'total_spent': total_spent,
            'categories_data': categories_data,
            'highest_category': highest_category,
            'lowest_category': lowest_category,
            'start_date': start_date,
            'end_date': end_date,
            'date_filter': date_filter,
            'sort_by': sort_by,
            'search': search,
            'spent_min': spent_min,
            'spent_max': spent_max,
            'count_min': count_min,
            'count_max': count_max,
        })
        
        return context


class CategoryCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'categories/category_form.html'
    success_url = reverse_lazy('category-list')
    success_message = "Category created successfully!"

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class CategoryUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'categories/category_form.html'
    success_url = reverse_lazy('category-list')
    success_message = "Category updated successfully!"

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)


class CategoryDeleteView(LoginRequiredMixin, DeleteView):
    model = Category
    template_name = 'categories/category_confirm_delete.html'
    success_url = reverse_lazy('category-list')

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Category deleted successfully!")
        return super().delete(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, "Category deleted successfully!")
        return super().form_valid(form)

    def form_valid(self, form):
        messages.success(self.request, "Category deleted successfully!")
        return super().form_valid(form)
