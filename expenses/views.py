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


class ExpenseListView(LoginRequiredMixin, ListView):
    model = Expense
    template_name = 'expenses/expense_list.html'
    context_object_name = 'expenses'
    paginate_by = 15

    def get_queryset(self):
        qs = Expense.objects.filter(user=self.request.user).order_by('-date', '-created_at')
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
        context['total_expense'] = filtered_qs.aggregate(t=Sum('amount'))['t'] or 0
        context['total_count'] = filtered_qs.count()

        # Pass filter values back to template
        params = self.request.GET
        context['search'] = params.get('search', '')
        context['category_id'] = params.get('category', '')
        context['date_from'] = params.get('date_from', '')
        context['date_to'] = params.get('date_to', '')
        context['amount_min'] = params.get('amount_min', '')
        context['amount_max'] = params.get('amount_max', '')

        # Categories for this user (dropdown)
        context['categories'] = Category.objects.filter(user=self.request.user).order_by('name')

        # Build query string without 'page' for pagination links
        query_params = params.copy()
        query_params.pop('page', None)
        context['query_string'] = query_params.urlencode()

        # Active filter summary
        filters = []
        if context['search']:
            filters.append(f'Search: "{context["search"]}"')
        if context['category_id']:
            if context['category_id'] == '__none__':
                filters.append('Category: Uncategorized')
            else:
                try:
                    cat = Category.objects.get(pk=int(context['category_id']), user=self.request.user)
                    filters.append(f'Category: {cat.name}')
                except (Category.DoesNotExist, ValueError):
                    pass
        if context['date_from'] or context['date_to']:
            date_range = f'{context["date_from"] or "start"} to {context["date_to"] or "today"}'
            filters.append(f'Date: {date_range}')
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
