from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.db.models import Sum, Count, Q
from django.utils import timezone

from .models import Goal
from .forms import GoalForm, GoalQuickUpdateForm

class GoalListView(LoginRequiredMixin, ListView):
    model = Goal
    template_name = 'goals/goal_list.html'
    context_object_name = 'goals'

    def get_queryset(self):
        qs = Goal.objects.filter(user=self.request.user)
        search = self.request.GET.get('search', '').strip()
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))
        
        status_filter = self.request.GET.get('status', 'all').strip().lower()
        if status_filter == 'completed':
            qs = [g for g in qs if g.is_completed]
        elif status_filter == 'active':
            qs = [g for g in qs if not g.is_completed]
        
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_user_goals = Goal.objects.filter(user=self.request.user)

        # Calculate dashboard metrics
        total_target = all_user_goals.aggregate(total=Sum('target_amount'))['total'] or Decimal('0.00')
        total_saved = all_user_goals.aggregate(total=Sum('current_amount'))['total'] or Decimal('0.00')
        
        completed_count = sum(1 for g in all_user_goals if g.is_completed)
        active_count = all_user_goals.count() - completed_count
        
        # Calculate overall remaining savings needed
        total_remaining = sum(g.remaining_amount for g in all_user_goals)

        context.update({
            'total_target': total_target,
            'total_saved': total_saved,
            'total_remaining': total_remaining,
            'completed_count': completed_count,
            'active_count': active_count,
            'total_goals_count': all_user_goals.count(),
            'search': self.request.GET.get('search', '').strip(),
            'status': self.request.GET.get('status', 'all').strip(),
            'today': timezone.localdate(),
        })
        return context


class GoalDetailView(LoginRequiredMixin, DetailView):
    model = Goal
    template_name = 'goals/goal_detail.html'
    context_object_name = 'goal'

    def get_queryset(self):
        return Goal.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['quick_update_form'] = GoalQuickUpdateForm(instance=self.get_object())
        return context

    def post(self, request, *args, **kwargs):
        goal = self.get_object()
        form = GoalQuickUpdateForm(request.POST, instance=goal)
        if form.is_valid():
            form.save()
            messages.success(request, f"Saved amount for '{goal.name}' updated successfully!")
            return redirect('goal-detail', pk=goal.pk)
        else:
            messages.error(request, "Failed to update saved amount. Please enter a valid number.")
            return redirect('goal-detail', pk=goal.pk)


class GoalCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Goal
    form_class = GoalForm
    template_name = 'goals/goal_form.html'
    success_url = reverse_lazy('goal-list')
    success_message = "Savings Goal created successfully!"

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class GoalUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Goal
    form_class = GoalForm
    template_name = 'goals/goal_form.html'
    success_url = reverse_lazy('goal-list')
    success_message = "Savings Goal updated successfully!"

    def get_queryset(self):
        return Goal.objects.filter(user=self.request.user)


class GoalDeleteView(LoginRequiredMixin, DeleteView):
    model = Goal
    template_name = 'goals/goal_confirm_delete.html'
    success_url = reverse_lazy('goal-list')

    def get_queryset(self):
        return Goal.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Savings Goal deleted successfully!")
        return super().delete(request, *args, **kwargs)
