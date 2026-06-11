from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.db.models import Sum, Q
from django.utils import timezone
import datetime

from .models import RecurringTransaction, GeneratedOccurrence, add_months
from .forms import RecurringTransactionForm
from .utils import generate_recurring_transactions

class RecurringTransactionListView(LoginRequiredMixin, ListView):
    model = RecurringTransaction
    template_name = 'recurrences/recurring_transaction_list.html'
    context_object_name = 'recurrences'

    def get_queryset(self):
        # Force running the generator to ensure transactions are up to date
        generate_recurring_transactions(self.request.user)

        qs = RecurringTransaction.objects.filter(user=self.request.user)

        # Search Query
        search = self.request.GET.get('search', '').strip()
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(notes__icontains=search))

        # Filters
        tx_type = self.request.GET.get('type', 'all').strip()
        if tx_type in ['Income', 'Expense']:
            qs = qs.filter(transaction_type=tx_type)

        frequency = self.request.GET.get('frequency', 'all').strip()
        if frequency in ['Daily', 'Weekly', 'Monthly', 'Quarterly', 'Yearly']:
            qs = qs.filter(frequency=frequency)

        status = self.request.GET.get('status', 'all').strip()
        if status in ['Active', 'Inactive']:
            qs = qs.filter(status=status)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        all_user_recurrences = RecurringTransaction.objects.filter(user=user)

        # Dashboard Card calculations (Active ones only)
        active_recurrences = all_user_recurrences.filter(status='Active')
        active_count = active_recurrences.count()
        inactive_count = all_user_recurrences.filter(status='Inactive').count()

        monthly_income = sum(r.monthly_equivalent for r in active_recurrences if r.transaction_type == 'Income')
        monthly_expense = sum(r.monthly_equivalent for r in active_recurrences if r.transaction_type == 'Expense')
        net_cashflow = monthly_income - monthly_expense

        # Upcoming transactions timeline in the next 30 days
        today = timezone.localdate()
        start_from = today + datetime.timedelta(days=1)
        end_at = today + datetime.timedelta(days=30)
        
        upcoming = []
        for recur in active_recurrences:
            # Calculate expected dates in the future [start_from, end_at]
            limit_date = min(end_at, recur.end_date) if recur.end_date else end_at
            if recur.start_date > limit_date:
                continue

            curr = recur.start_date
            i = 0
            while curr <= limit_date:
                if curr >= start_from:
                    upcoming.append({
                        'recurring_transaction': recur,
                        'date': curr,
                        'name': recur.name,
                        'amount': recur.amount,
                        'type': recur.transaction_type,
                        'frequency': recur.frequency,
                    })
                i += 1
                if recur.frequency == 'Daily':
                    curr = recur.start_date + datetime.timedelta(days=i)
                elif recur.frequency == 'Weekly':
                    curr = recur.start_date + datetime.timedelta(weeks=i)
                elif recur.frequency == 'Monthly':
                    curr = add_months(recur.start_date, i)
                elif recur.frequency == 'Quarterly':
                    curr = add_months(recur.start_date, i * 3)
                elif recur.frequency == 'Yearly':
                    curr = add_months(recur.start_date, i * 12)

        # Sort upcoming by date
        upcoming.sort(key=lambda x: x['date'])
        
        context.update({
            'active_count': active_count,
            'inactive_count': inactive_count,
            'monthly_income': monthly_income,
            'monthly_expense': monthly_expense,
            'net_cashflow': net_cashflow,
            'upcoming_transactions': upcoming[:15],  # limit to top 15
            'search': self.request.GET.get('search', '').strip(),
            'type': self.request.GET.get('type', 'all').strip(),
            'frequency': self.request.GET.get('frequency', 'all').strip(),
            'status': self.request.GET.get('status', 'all').strip(),
            'today': today,
        })
        return context


class RecurringTransactionDetailView(LoginRequiredMixin, DetailView):
    model = RecurringTransaction
    template_name = 'recurrences/recurring_transaction_detail.html'
    context_object_name = 'recurrence'

    def get_queryset(self):
        return RecurringTransaction.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Fetch the logs of generated occurrences
        context['occurrences'] = GeneratedOccurrence.objects.filter(recurring_transaction=self.get_object())
        return context


class RecurringTransactionCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = RecurringTransaction
    form_class = RecurringTransactionForm
    template_name = 'recurrences/recurring_transaction_form.html'
    success_url = reverse_lazy('recurring-list')
    success_message = "Recurring Transaction configuration created successfully!"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        # Proactively trigger generation for new configuration
        generate_recurring_transactions(self.request.user)
        return response


class RecurringTransactionUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = RecurringTransaction
    form_class = RecurringTransactionForm
    template_name = 'recurrences/recurring_transaction_form.html'
    success_url = reverse_lazy('recurring-list')
    success_message = "Recurring Transaction configuration updated successfully!"

    def get_queryset(self):
        return RecurringTransaction.objects.filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        # Proactively trigger generation for updated configuration
        generate_recurring_transactions(self.request.user)
        return response


class RecurringTransactionDeleteView(LoginRequiredMixin, DeleteView):
    model = RecurringTransaction
    template_name = 'recurrences/recurring_transaction_confirm_delete.html'
    success_url = reverse_lazy('recurring-list')

    def get_queryset(self):
        return RecurringTransaction.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Recurring Transaction configuration deleted successfully!")
        return super().delete(request, *args, **kwargs)


class RecurringTransactionToggleView(LoginRequiredMixin, DetailView):
    model = RecurringTransaction

    def get_queryset(self):
        return RecurringTransaction.objects.filter(user=self.request.user)

    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.status == 'Active':
            obj.status = 'Inactive'
            messages.success(request, f"Recurring transaction '{obj.name}' has been paused.")
        else:
            obj.status = 'Active'
            messages.success(request, f"Recurring transaction '{obj.name}' has been reactivated.")
        obj.save()
        return redirect('recurring-detail', pk=obj.pk)
