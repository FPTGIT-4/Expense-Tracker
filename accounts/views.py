from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import User
from django.views.generic import CreateView, TemplateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django import forms


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
