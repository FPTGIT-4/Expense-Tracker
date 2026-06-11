import datetime
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.db.models import Sum, Count, Q
from django.utils import timezone

from .models import CompanyAccount, CompanyIncome, CompanyExpense
from .forms import CompanyAccountForm, CompanyIncomeForm, CompanyExpenseForm
from categories.models import Category

def get_company_date_range(request):
    """
    Helper to extract start/end date for company analytics and reports.
    """
    today = timezone.localdate()
    date_filter = request.GET.get('date_filter', 'this_month').strip().lower()
    
    if date_filter == 'today':
        return today, today, 'today'
    elif date_filter == 'this_week':
        start = today - datetime.timedelta(days=today.weekday())
        return start, today, 'this_week'
    elif date_filter == 'this_month':
        start = today.replace(day=1)
        return start, today, 'this_month'
    elif date_filter == 'this_year':
        start = today.replace(month=1, day=1)
        return start, today, 'this_year'
    elif date_filter == 'custom':
        date_from = request.GET.get('date_from', '').strip()
        date_to = request.GET.get('date_to', '').strip()
        start = today
        end = today
        if date_from:
            try:
                start = datetime.datetime.strptime(date_from, '%Y-%m-%d').date()
            except ValueError:
                pass
        if date_to:
            try:
                end = datetime.datetime.strptime(date_to, '%Y-%m-%d').date()
            except ValueError:
                pass
        return start, end, 'custom'
        
    start = today.replace(day=1)
    return start, today, 'this_month'


# ── Company Accounts CRUD ─────────────────────────────────────────────────────

class CompanyAccountListView(LoginRequiredMixin, ListView):
    model = CompanyAccount
    template_name = 'companies/company_account_list.html'
    context_object_name = 'company_accounts'

    def get_queryset(self):
        return CompanyAccount.objects.filter(user=self.request.user).order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        accounts = self.get_queryset()
        
        # Aggregate statistics across all company accounts
        total_opening = accounts.aggregate(total=Sum('opening_balance'))['total'] or Decimal('0.00')
        total_income = CompanyIncome.objects.filter(company_account__user=self.request.user).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        total_expenses = CompanyExpense.objects.filter(company_account__user=self.request.user).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        total_balance = total_opening + total_income - total_expenses

        context.update({
            'total_opening': total_opening,
            'total_income': total_income,
            'total_expenses': total_expenses,
            'total_balance': total_balance,
        })
        return context


class CompanyAccountCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = CompanyAccount
    form_class = CompanyAccountForm
    template_name = 'companies/company_account_form.html'
    success_url = reverse_lazy('company-account-list')
    success_message = "Company Account created successfully!"

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class CompanyAccountUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = CompanyAccount
    form_class = CompanyAccountForm
    template_name = 'companies/company_account_form.html'
    success_url = reverse_lazy('company-account-list')
    success_message = "Company Account updated successfully!"

    def get_queryset(self):
        return CompanyAccount.objects.filter(user=self.request.user)


class CompanyAccountDeleteView(LoginRequiredMixin, DeleteView):
    model = CompanyAccount
    template_name = 'companies/company_account_confirm_delete.html'
    success_url = reverse_lazy('company-account-list')

    def get_queryset(self):
        return CompanyAccount.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Company Account deleted successfully!")
        return super().delete(request, *args, **kwargs)


class CompanyAccountDetailView(LoginRequiredMixin, DetailView):
    model = CompanyAccount
    template_name = 'companies/company_account_detail.html'
    context_object_name = 'company'

    def get_queryset(self):
        return CompanyAccount.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = self.get_object()
        
        # Retrieve recent transactions specifically for this company account
        db_incomes = CompanyIncome.objects.filter(company_account=company).order_by('-date', '-created_at')[:10]
        db_expenses = CompanyExpense.objects.filter(company_account=company).select_related('category').order_by('-date', '-created_at')[:10]

        recent_txs = []
        for inc in db_incomes:
            recent_txs.append({
                'id': inc.id,
                'date': inc.date,
                'created_at': inc.created_at,
                'type': 'Income',
                'amount': inc.amount,
                'category_or_source': inc.source,
                'description': inc.description,
                'edit_url_name': 'company-income-edit',
                'delete_url_name': 'company-income-delete',
            })
        for exp in db_expenses:
            recent_txs.append({
                'id': exp.id,
                'date': exp.date,
                'created_at': exp.created_at,
                'type': 'Expense',
                'amount': exp.amount,
                'category_or_source': exp.category.name if exp.category else 'Uncategorized',
                'description': exp.description,
                'edit_url_name': 'company-expense-edit',
                'delete_url_name': 'company-expense-delete',
            })

        recent_txs.sort(key=lambda x: (x['date'], x['created_at']), reverse=True)

        context.update({
            'recent_transactions': recent_txs[:15],
            'total_income': company.total_income,
            'total_expenses': company.total_expenses,
        })
        return context


# ── Company Income CRUD ───────────────────────────────────────────────────────

class CompanyIncomeCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = CompanyIncome
    form_class = CompanyIncomeForm
    template_name = 'companies/company_transaction_form.html'
    success_message = "Income logged successfully!"

    def get_initial(self):
        initial = super().get_initial()
        company_id = self.request.GET.get('company_account')
        if company_id:
            initial['company_account'] = company_id
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        return reverse_lazy('company-dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['transaction_type'] = 'Income'
        context['title_text'] = 'Log Business Income'
        return context


class CompanyIncomeUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = CompanyIncome
    form_class = CompanyIncomeForm
    template_name = 'companies/company_transaction_form.html'
    success_message = "Income updated successfully!"

    def get_queryset(self):
        return CompanyIncome.objects.filter(company_account__user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        return reverse_lazy('company-dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['transaction_type'] = 'Income'
        context['title_text'] = 'Edit Business Income'
        return context


class CompanyIncomeDeleteView(LoginRequiredMixin, DeleteView):
    model = CompanyIncome
    template_name = 'companies/company_account_confirm_delete.html'

    def get_queryset(self):
        return CompanyIncome.objects.filter(company_account__user=self.request.user)

    def get_success_url(self):
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        return reverse_lazy('company-dashboard')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Income transaction deleted successfully!")
        return super().delete(request, *args, **kwargs)


# ── Company Expense CRUD ──────────────────────────────────────────────────────

class CompanyExpenseCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = CompanyExpense
    form_class = CompanyExpenseForm
    template_name = 'companies/company_transaction_form.html'
    success_message = "Expense logged successfully!"

    def get_initial(self):
        initial = super().get_initial()
        company_id = self.request.GET.get('company_account')
        if company_id:
            initial['company_account'] = company_id
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        return reverse_lazy('company-dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['transaction_type'] = 'Expense'
        context['title_text'] = 'Log Business Expense'
        return context


class CompanyExpenseUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = CompanyExpense
    form_class = CompanyExpenseForm
    template_name = 'companies/company_transaction_form.html'
    success_message = "Expense updated successfully!"

    def get_queryset(self):
        return CompanyExpense.objects.filter(company_account__user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        return reverse_lazy('company-dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['transaction_type'] = 'Expense'
        context['title_text'] = 'Edit Business Expense'
        return context


class CompanyExpenseDeleteView(LoginRequiredMixin, DeleteView):
    model = CompanyExpense
    template_name = 'companies/company_account_confirm_delete.html'

    def get_queryset(self):
        return CompanyExpense.objects.filter(company_account__user=self.request.user)

    def get_success_url(self):
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        return reverse_lazy('company-dashboard')

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Expense transaction deleted successfully!")
        return super().delete(request, *args, **kwargs)


# ── Company Dashboard ─────────────────────────────────────────────────────────

class CompanyDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'companies/company_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Fetch all company accounts
        accounts = CompanyAccount.objects.filter(user=user)
        active_accounts = accounts.filter(status='ACTIVE')
        
        # Executive aggregated metrics
        total_opening = accounts.aggregate(total=Sum('opening_balance'))['total'] or Decimal('0.00')
        total_income = CompanyIncome.objects.filter(company_account__user=user).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        total_expenses = CompanyExpense.objects.filter(company_account__user=user).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        current_balance = total_opening + total_income - total_expenses

        # Recent activities (combined)
        db_incomes = CompanyIncome.objects.filter(company_account__user=user).select_related('company_account').order_by('-date', '-created_at')[:10]
        db_expenses = CompanyExpense.objects.filter(company_account__user=user).select_related('company_account', 'category').order_by('-date', '-created_at')[:10]

        recent_txs = []
        for inc in db_incomes:
            recent_txs.append({
                'id': inc.id,
                'date': inc.date,
                'created_at': inc.created_at,
                'type': 'Income',
                'amount': inc.amount,
                'category_or_source': inc.source,
                'description': inc.description,
                'company_account': inc.company_account,
                'edit_url_name': 'company-income-edit',
                'delete_url_name': 'company-income-delete',
            })
        for exp in db_expenses:
            recent_txs.append({
                'id': exp.id,
                'date': exp.date,
                'created_at': exp.created_at,
                'type': 'Expense',
                'amount': exp.amount,
                'category_or_source': exp.category.name if exp.category else 'Uncategorized',
                'description': exp.description,
                'company_account': exp.company_account,
                'edit_url_name': 'company-expense-edit',
                'delete_url_name': 'company-expense-delete',
            })

        recent_txs.sort(key=lambda x: (x['date'], x['created_at']), reverse=True)

        context.update({
            'accounts': accounts,
            'active_accounts': active_accounts,
            'total_income': total_income,
            'total_expenses': total_expenses,
            'current_balance': current_balance,
            'recent_transactions': recent_txs[:15],
            'today': timezone.localdate(),
        })
        return context


# ── Company Reports ───────────────────────────────────────────────────────────

class CompanyReportsView(LoginRequiredMixin, TemplateView):
    template_name = 'companies/company_reports.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Load user company accounts for the filter dropdown
        company_accounts = CompanyAccount.objects.filter(user=user)
        context['company_accounts'] = company_accounts

        # Parse filter parameters
        active_company_id = self.request.GET.get('company', 'all').strip()
        start_date, end_date, date_filter = get_company_date_range(self.request)

        # Base querysets for filtered transactions
        income_qs = CompanyIncome.objects.filter(company_account__user=user, date__range=(start_date, end_date))
        expense_qs = CompanyExpense.objects.filter(company_account__user=user, date__range=(start_date, end_date)).select_related('category')

        if active_company_id and active_company_id != 'all':
            try:
                company_id = int(active_company_id)
                income_qs = income_qs.filter(company_account_id=company_id)
                expense_qs = expense_qs.filter(company_account_id=company_id)
                selected_company = company_accounts.filter(pk=company_id).first()
            except ValueError:
                selected_company = None
        else:
            selected_company = None

        # Execute sums
        total_income = income_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        total_expenses = expense_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        net_balance = total_income - total_expenses

        # Category-wise Expense Report
        category_report = []
        if total_expenses > 0:
            cat_sums = expense_qs.values('category__name').annotate(total=Sum('amount')).order_by('-total')
            for item in cat_sums:
                name = item['category__name'] or 'Uncategorized'
                amt = item['total']
                pct = (amt / total_expenses) * 100
                category_report.append({
                    'name': name,
                    'amount': amt,
                    'percentage': pct
                })

        # Source-wise Income Report
        source_report = []
        source_sums = income_qs.values('source').annotate(total=Sum('amount')).order_by('-total')
        for item in source_sums:
            source_report.append({
                'source': item['source'],
                'amount': item['total']
            })

        # Combined transaction timeline
        timeline_txs = []
        for inc in income_qs.select_related('company_account'):
            timeline_txs.append({
                'date': inc.date,
                'created_at': inc.created_at,
                'type': 'Income',
                'amount': inc.amount,
                'category_or_source': inc.source,
                'description': inc.description,
                'company_account': inc.company_account,
            })
        for exp in expense_qs.select_related('company_account', 'category'):
            timeline_txs.append({
                'date': exp.date,
                'created_at': exp.created_at,
                'type': 'Expense',
                'amount': exp.amount,
                'category_or_source': exp.category.name if exp.category else 'Uncategorized',
                'description': exp.description,
                'company_account': exp.company_account,
            })
        timeline_txs.sort(key=lambda x: (x['date'], x['created_at']), reverse=True)

        context.update({
            'total_income': total_income,
            'total_expenses': total_expenses,
            'net_balance': net_balance,
            'category_report': category_report,
            'source_report': source_report,
            'recent_transactions': timeline_txs,
            'selected_company': selected_company,
            'active_company_id': active_company_id,
            'start_date': start_date,
            'end_date': end_date,
            'date_filter': date_filter,
            'start_date_val': start_date.strftime('%Y-%m-%d'),
            'end_date_val': end_date.strftime('%Y-%m-%d'),
        })
        return context
