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
        qs = Expense.objects.filter(user=self.request.user).select_related('category')
        
        # Keep only Today, This Week, and This Month filters
        date_filter = self.request.GET.get('date_filter', 'this_month').strip().lower()
        if date_filter not in ['today', 'this_week', 'this_month']:
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
        total_expense = queryset.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        context.update({
            'start_date': start_date,
            'end_date': end_date,
            'date_filter': date_filter,
            'total_expense': total_expense,
        })
        return context


class ExpenseCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Expense
    form_class = ExpenseForm
    template_name = 'expenses/expense_form.html'
    success_url = reverse_lazy('expense-list')
    success_message = "Expense record created successfully!"

    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        
        post_data = self.request.POST
        row_indices_str = post_data.get('new_row_indices', '')
        if row_indices_str:
            from categories.models import Category, Label
            from decimal import Decimal
            
            indices = [int(idx) for idx in row_indices_str.split(',') if idx.strip()]
            for idx in indices:
                amount_str = post_data.get(f'amount_new_{idx}', '').strip()
                cat_id = post_data.get(f'category_new_{idx}', '').strip()
                lbl_ids = post_data.getlist(f'labels_new_{idx}')
                desc = post_data.get(f'description_new_{idx}', '').strip()
                
                if amount_str and cat_id:
                    try:
                        amount = Decimal(amount_str)
                        category = Category.objects.get(pk=int(cat_id), user=self.request.user)
                        
                        date = form.cleaned_data.get('date')
                        account = form.cleaned_data.get('account')
                        
                        new_expense = Expense.objects.create(
                            user=self.request.user,
                            account=account,
                            name=category.name,
                            amount=amount,
                            date=date,
                            category=category,
                            description=desc if desc else None
                        )
                        
                        if lbl_ids:
                            labels = Label.objects.filter(pk__in=[int(lid) for lid in lbl_ids if lid.strip()], user=self.request.user)
                            new_expense.labels.set(labels)
                    except Exception as e:
                        pass
        return response

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

    def form_valid(self, form):
        response = super().form_valid(form)
        
        post_data = self.request.POST
        row_indices_str = post_data.get('new_row_indices', '')
        if row_indices_str:
            from categories.models import Category, Label
            from decimal import Decimal
            
            indices = [int(idx) for idx in row_indices_str.split(',') if idx.strip()]
            for idx in indices:
                amount_str = post_data.get(f'amount_new_{idx}', '').strip()
                cat_id = post_data.get(f'category_new_{idx}', '').strip()
                lbl_ids = post_data.getlist(f'labels_new_{idx}')
                desc = post_data.get(f'description_new_{idx}', '').strip()
                
                if amount_str and cat_id:
                    try:
                        amount = Decimal(amount_str)
                        category = Category.objects.get(pk=int(cat_id), user=self.request.user)
                        
                        date = form.cleaned_data.get('date')
                        account = form.cleaned_data.get('account')
                        
                        new_expense = Expense.objects.create(
                            user=self.request.user,
                            account=account,
                            name=category.name,
                            amount=amount,
                            date=date,
                            category=category,
                            description=desc if desc else None
                        )
                        
                        if lbl_ids:
                            labels = Label.objects.filter(pk__in=[int(lid) for lid in lbl_ids if lid.strip()], user=self.request.user)
                            new_expense.labels.set(labels)
                    except Exception as e:
                        pass
        return response


class ExpenseDeleteView(LoginRequiredMixin, DeleteView):
    model = Expense
    template_name = 'expenses/expense_confirm_delete.html'
    success_url = reverse_lazy('expense-list')

    def get_queryset(self):
        return Expense.objects.filter(user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Expense record deleted successfully!")
        return super().form_valid(form)
