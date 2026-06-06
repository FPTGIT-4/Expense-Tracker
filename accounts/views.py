from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import User
from django.views.generic import CreateView, TemplateView, UpdateView, ListView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django import forms
from .models import Account
from .forms import AccountForm
from decimal import Decimal


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
