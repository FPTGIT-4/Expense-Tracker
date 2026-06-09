from django.shortcuts import render
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.db.models import Q
import calendar
import datetime

from .models import Budget
from .forms import BudgetForm

class BudgetListView(LoginRequiredMixin, ListView):
    model = Budget
    template_name = 'budgets/budget_list.html'
    context_object_name = 'budgets'
    paginate_by = 10

    def get_queryset(self):
        queryset = Budget.objects.filter(user=self.request.user).select_related('category')
        
        # Search filter
        search = self.request.GET.get('search', '').strip()
        if search:
            queryset = queryset.filter(category__name__icontains=search)
            
        # Month filter
        month = self.request.GET.get('month', '').strip()
        if month:
            try:
                queryset = queryset.filter(month=int(month))
            except ValueError:
                pass
                
        # Year filter
        year = self.request.GET.get('year', '').strip()
        if year:
            try:
                queryset = queryset.filter(year=int(year))
            except ValueError:
                pass
                
        # Status/Active filter
        status = self.request.GET.get('status', '').strip()
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
            
        # Sort by status rank: Exceeded first, then Warning, then Normal.
        def budget_status_rank(b):
            stat = b.status_text
            if stat == 'Exceeded':
                return 0
            elif stat == 'Warning':
                return 1
            else:
                return 2
                
        return sorted(queryset, key=budget_status_rank)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Prepare choices for filter controls
        context['months'] = [(i, calendar.month_name[i]) for i in range(1, 13)]
        
        # Year range from database or current range
        current_year = datetime.datetime.now().year
        years_qs = Budget.objects.filter(user=self.request.user).values_list('year', flat=True).distinct()
        years = list(years_qs)
        if current_year not in years:
            years.append(current_year)
        years.sort(reverse=True)
        context['years'] = years
        
        # Keep query parameters for pagination links
        params = self.request.GET.copy()
        params.pop('page', None)
        context['query_string'] = params.urlencode()
        
        # Active filter flags
        context['search_val'] = self.request.GET.get('search', '').strip()
        context['month_val'] = self.request.GET.get('month', '').strip()
        context['year_val'] = self.request.GET.get('year', '').strip()
        context['status_val'] = self.request.GET.get('status', '').strip()
        
        # High level summary cards for matching budgets
        user_budgets = Budget.objects.filter(user=self.request.user, is_active=True)
        
        # Apply current filters for summary if desired, or keep general
        # Let's filter general active budgets for current month/year
        now = datetime.datetime.now()
        cur_month = now.month
        cur_year = now.year
        
        # Allow checking if selected month/year is in URL
        if context['month_val']:
            try: cur_month = int(context['month_val'])
            except ValueError: pass
        if context['year_val']:
            try: cur_year = int(context['year_val'])
            except ValueError: pass
            
        context['total_budgets_count'] = Budget.get_total_budgets(self.request.user, month=cur_month, year=cur_year)
        context['total_budget_amount'] = Budget.get_total_budget_amount(self.request.user, month=cur_month, year=cur_year)
        context['total_spent'] = Budget.get_total_spent(self.request.user, month=cur_month, year=cur_year)
        context['total_remaining'] = Budget.get_total_remaining(self.request.user, month=cur_month, year=cur_year)
        
        # Get overall usage percentage
        if context['total_budget_amount'] > 0:
            context['overall_usage_pct'] = (context['total_spent'] / context['total_budget_amount']) * 100
        else:
            context['overall_usage_pct'] = 0.0
            
        context['current_month_name'] = calendar.month_name[cur_month]
        context['current_year'] = cur_year
        
        return context


class BudgetDetailView(LoginRequiredMixin, DetailView):
    model = Budget
    template_name = 'budgets/budget_detail.html'
    context_object_name = 'budget'

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user).select_related('category')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        budget = self.object
        
        # Add monthly name
        context['month_name'] = calendar.month_name[budget.month]
        
        # Fetch actual transactions in this budget's category, month, and year for display
        from expenses.models import Expense
        context['recent_expenses'] = Expense.objects.filter(
            user=self.request.user,
            category=budget.category,
            date__month=budget.month,
            date__year=budget.year
        ).order_by('-date', '-created_at')[:5]
        
        return context


class BudgetCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Budget
    form_class = BudgetForm
    template_name = 'budgets/budget_form.html'
    success_url = reverse_lazy('budget-list')
    success_message = "Budget created successfully!"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class BudgetUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Budget
    form_class = BudgetForm
    template_name = 'budgets/budget_form.html'
    success_url = reverse_lazy('budget-list')
    success_message = "Budget updated successfully!"

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class BudgetDeleteView(LoginRequiredMixin, DeleteView):
    model = Budget
    template_name = 'budgets/budget_confirm_delete.html'
    success_url = reverse_lazy('budget-list')

    def get_queryset(self):
        return Budget.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Budget deleted successfully!")
        return super().delete(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, "Budget deleted successfully!")
        return super().form_valid(form)
