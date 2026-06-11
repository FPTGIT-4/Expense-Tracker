from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.db.models import Sum, Q
from django.utils import timezone

from .models import Debt, Repayment
from .forms import DebtForm, RepaymentForm

class DebtListView(LoginRequiredMixin, ListView):
    model = Debt
    template_name = 'debts/debt_list.html'
    context_object_name = 'debts'

    def get_queryset(self):
        qs = Debt.objects.filter(user=self.request.user)
        
        # Search query
        search = self.request.GET.get('search', '').strip()
        if search:
            qs = qs.filter(Q(person_name__icontains=search) | Q(notes__icontains=search))
            
        # Debt Type Filter
        debt_type = self.request.GET.get('debt_type', 'all').strip()
        if debt_type in ['Borrowed', 'Lent']:
            qs = qs.filter(debt_type=debt_type)
            
        # Status Filter
        status = self.request.GET.get('status', 'all').strip()
        if status == 'Active':
            qs = qs.filter(status='Active')
        elif status == 'Settled':
            qs = qs.filter(status='Settled')
        elif status == 'Overdue':
            qs = qs.filter(status='Active', due_date__lt=timezone.localdate())
            
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_user_debts = Debt.objects.filter(user=self.request.user)

        # Aggregate totals
        total_borrowed = all_user_debts.filter(debt_type='Borrowed').aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        total_lent = all_user_debts.filter(debt_type='Lent').aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        # Outstanding balances (Remaining to pay and receive)
        active_borrowed = all_user_debts.filter(user=self.request.user, debt_type='Borrowed')
        total_to_pay = sum(d.remaining_balance for d in active_borrowed)

        active_lent = all_user_debts.filter(user=self.request.user, debt_type='Lent')
        total_to_receive = sum(d.remaining_balance for d in active_lent)

        # Active & Settled counts
        active_count = all_user_debts.filter(status='Active').count()
        settled_count = all_user_debts.filter(status='Settled').count()
        overdue_count = all_user_debts.filter(status='Active', due_date__lt=timezone.localdate()).count()

        context.update({
            'total_borrowed': total_borrowed,
            'total_lent': total_lent,
            'total_to_pay': total_to_pay,
            'total_to_receive': total_to_receive,
            'active_count': active_count,
            'settled_count': settled_count,
            'overdue_count': overdue_count,
            'search': self.request.GET.get('search', '').strip(),
            'debt_type': self.request.GET.get('debt_type', 'all').strip(),
            'status': self.request.GET.get('status', 'all').strip(),
            'today': timezone.localdate(),
        })
        return context


class DebtDetailView(LoginRequiredMixin, DetailView):
    model = Debt
    template_name = 'debts/debt_detail.html'
    context_object_name = 'debt'

    def get_queryset(self):
        return Debt.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Check if form is already in context (from failed POST validation)
        if 'form' not in context:
            context['form'] = RepaymentForm(debt=self.get_object())
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = RepaymentForm(request.POST, debt=self.object)
        if form.is_valid():
            repayment = form.save(commit=False)
            repayment.debt = self.object
            repayment.save()
            messages.success(request, f"Repayment of {repayment.amount} recorded successfully.")
            return redirect('debt-detail', pk=self.object.pk)
        else:
            messages.error(request, "Failed to record repayment. Please review the errors below.")
            context = self.get_context_data(form=form)
            return self.render_to_response(context)


class DebtCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Debt
    form_class = DebtForm
    template_name = 'debts/debt_form.html'
    success_url = reverse_lazy('debt-list')
    success_message = "Debt record created successfully!"

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class DebtUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Debt
    form_class = DebtForm
    template_name = 'debts/debt_form.html'
    success_url = reverse_lazy('debt-list')
    success_message = "Debt record updated successfully!"

    def get_queryset(self):
        return Debt.objects.filter(user=self.request.user)


class DebtDeleteView(LoginRequiredMixin, DeleteView):
    model = Debt
    template_name = 'debts/debt_confirm_delete.html'
    success_url = reverse_lazy('debt-list')

    def get_queryset(self):
        return Debt.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Debt record deleted successfully!")
        return super().delete(request, *args, **kwargs)


class RepaymentDeleteView(LoginRequiredMixin, DeleteView):
    model = Repayment
    template_name = 'debts/repayment_confirm_delete.html'

    def get_queryset(self):
        return Repayment.objects.filter(debt__user=self.request.user)

    def get_success_url(self):
        return reverse_lazy('debt-detail', kwargs={'pk': self.object.debt.pk})

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Repayment record deleted successfully!")
        return super().delete(request, *args, **kwargs)
