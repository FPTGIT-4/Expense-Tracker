from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import User
from django.views.generic import CreateView, TemplateView, UpdateView, ListView, DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django import forms
from .models import Account, AccountTransfer
from .forms import AccountForm, TransferForm
from decimal import Decimal
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.utils import timezone
import datetime


# ── Profile edit form (only Full Name + Email) ────────────────────────────────
class ProfileEditForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=150, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control bg-dark-custom text-white border-glass',
            'placeholder': 'First name',
        })
    )
    last_name = forms.CharField(
        max_length=150, required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control bg-dark-custom text-white border-glass',
            'placeholder': 'Last name',
        })
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control bg-dark-custom text-white border-glass',
            'placeholder': 'your@email.com',
        })
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']


# ── Sign Up ───────────────────────────────────────────────────────────────────
class SignUpView(SuccessMessageMixin, CreateView):
    form_class = UserCreationForm
    template_name = 'registration/signup.html'
    success_url = reverse_lazy('login')
    success_message = "Your account was created successfully! You can now log in."


# ── Profile Details (view + edit) ─────────────────────────────────────────────
class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'registration/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = ProfileEditForm(instance=self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        form = ProfileEditForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('profile')
        return render(request, self.template_name, {'form': form})


# ── Financial Account Management CRUD ─────────────────────────────────────────
class AccountListView(LoginRequiredMixin, ListView):
    model = Account
    template_name = 'accounts/account_list.html'
    context_object_name = 'accounts'

    def get_queryset(self):
        # Automatically initialize a default Cash account if the user has no accounts
        if not Account.objects.filter(user=self.request.user).exists():
            Account.objects.create(
                user=self.request.user,
                name='Cash',
                account_type='Cash',
                initial_balance=Decimal('0.00')
            )
        return Account.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Calculate total balance
        accounts = self.get_queryset()
        total_balance = sum(acc.current_balance for acc in accounts)
        context['total_balance'] = total_balance
        return context


class AccountCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Account
    form_class = AccountForm
    template_name = 'accounts/account_form.html'
    success_url = reverse_lazy('account-list')
    success_message = "Account created successfully!"

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class AccountUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Account
    form_class = AccountForm
    template_name = 'accounts/account_form.html'
    success_url = reverse_lazy('account-list')
    success_message = "Account updated successfully!"

    def get_queryset(self):
        return Account.objects.filter(user=self.request.user)


class AccountDeleteView(LoginRequiredMixin, DeleteView):
    model = Account
    template_name = 'accounts/account_confirm_delete.html'
    success_url = reverse_lazy('account-list')

    def get_queryset(self):
        return Account.objects.filter(user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Account deleted successfully!")
        return super().form_valid(form)


class AccountDetailView(LoginRequiredMixin, DetailView):
    model = Account
    template_name = 'accounts/account_detail.html'
    context_object_name = 'account'

    def get_queryset(self):
        return Account.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        account = self.get_object()

        # Calculate Net Change
        net_change = account.current_balance - account.initial_balance
        context['net_change'] = net_change

        # Fetch and combine Incomes and Expenses
        incomes = account.incomes.all()
        expenses = account.expenses.select_related('category')

        tx_list = []
        for inc in incomes:
            tx_list.append({
                'date': inc.date,
                'created_at': inc.created_at,
                'type': 'Income',
                'category_or_source': inc.source,
                'description': inc.description,
                'amount': inc.amount,
            })

        for exp in expenses:
            tx_list.append({
                'date': exp.date,
                'created_at': exp.created_at,
                'type': 'Expense',
                'category_or_source': exp.category.name if exp.category else 'Uncategorized',
                'description': exp.description,
                'amount': exp.amount,
            })

        # Sort newest first
        tx_list.sort(key=lambda x: (x['date'], x['created_at']), reverse=True)

        # Paginate (10 transactions per page)
        paginator = Paginator(tx_list, 10)
        page = self.request.GET.get('page')
        try:
            transactions = paginator.page(page)
        except PageNotAnInteger:
            transactions = paginator.page(1)
        except EmptyPage:
            transactions = paginator.page(paginator.num_pages)

        context['transactions'] = transactions
        return context


class AccountTransferCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = AccountTransfer
    form_class = TransferForm
    template_name = 'accounts/account_transfer_form.html'
    success_url = reverse_lazy('account-list')
    success_message = "Money transferred successfully!"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class TransferListView(LoginRequiredMixin, ListView):
    model = AccountTransfer
    template_name = 'accounts/transfer_list.html'
    context_object_name = 'transfers'
    paginate_by = 10

    def get_queryset(self):
        queryset = AccountTransfer.objects.filter(user=self.request.user).select_related('from_account', 'to_account')

        # Search query
        q = self.request.GET.get('q', '').strip()
        if q:
            try:
                amount_val = float(q)
                queryset = queryset.filter(
                    Q(note__icontains=q) |
                    Q(from_account__name__icontains=q) |
                    Q(to_account__name__icontains=q) |
                    Q(amount=amount_val)
                )
            except ValueError:
                queryset = queryset.filter(
                    Q(note__icontains=q) |
                    Q(from_account__name__icontains=q) |
                    Q(to_account__name__icontains=q)
                )

        # Period filter
        period = self.request.GET.get('period', '').strip()
        today = timezone.localdate()
        if period == 'today':
            queryset = queryset.filter(transfer_date=today)
        elif period == 'week':
            start_week = today - datetime.timedelta(days=today.weekday())
            queryset = queryset.filter(transfer_date__gte=start_week, transfer_date__lte=today)
        elif period == 'month':
            queryset = queryset.filter(transfer_date__year=today.year, transfer_date__month=today.month)
        elif period == 'year':
            queryset = queryset.filter(transfer_date__year=today.year)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['q'] = self.request.GET.get('q', '').strip()
        context['period'] = self.request.GET.get('period', '').strip()
        return context


class TransferDetailView(LoginRequiredMixin, DetailView):
    model = AccountTransfer
    template_name = 'accounts/transfer_detail.html'
    context_object_name = 'transfer'

    def get_queryset(self):
        return AccountTransfer.objects.filter(user=self.request.user)
