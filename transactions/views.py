from django.shortcuts import render
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.forms import UserCreationForm
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from .models import Income
from .forms import IncomeForm

class IncomeListView(LoginRequiredMixin, ListView):
    model = Income
    template_name = 'transactions/income_list.html'
    context_object_name = 'incomes'

    def get_queryset(self):
        # Users can only view their own income records
        return Income.objects.filter(user=self.request.user).order_by('-date', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        incomes = self.get_queryset()
        context['total_income'] = sum(income.amount for income in incomes)
        return context


class IncomeCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Income
    form_class = IncomeForm
    template_name = 'transactions/income_form.html'
    success_url = reverse_lazy('income-list')
    success_message = "Income record created successfully!"

    def form_valid(self, form):
        # Automatically assign the current logged-in user as the owner of the record
        form.instance.user = self.request.user
        return super().form_valid(form)


class IncomeUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Income
    form_class = IncomeForm
    template_name = 'transactions/income_form.html'
    success_url = reverse_lazy('income-list')
    success_message = "Income record updated successfully!"

    def get_queryset(self):
        # Users can only edit their own income records
        return Income.objects.filter(user=self.request.user)


class IncomeDeleteView(LoginRequiredMixin, DeleteView):
    model = Income
    template_name = 'transactions/income_confirm_delete.html'
    success_url = reverse_lazy('income-list')

    def get_queryset(self):
        # Users can only delete their own income records
        return Income.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Income record deleted successfully!")
        return super().delete(request, *args, **kwargs)


class SignUpView(SuccessMessageMixin, CreateView):
    form_class = UserCreationForm
    template_name = 'registration/signup.html'
    success_url = reverse_lazy('login')
    success_message = "Your account was created successfully! You can now log in."
