from django import forms
from .models import Goal

class GoalForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = ['name', 'target_amount', 'current_amount', 'target_date', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'placeholder': 'Enter goal name (e.g. Emergency Fund, New Car)...',
            }),
            'target_amount': forms.NumberInput(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'placeholder': '0.00',
                'step': '0.01',
            }),
            'current_amount': forms.NumberInput(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'placeholder': '0.00',
                'step': '0.01',
            }),
            'target_date': forms.DateInput(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'type': 'date',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'placeholder': 'Enter goal description details (optional)...',
                'rows': 3,
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        target_amount = cleaned_data.get('target_amount')
        current_amount = cleaned_data.get('current_amount')
        
        if target_amount is not None and target_amount <= 0:
            self.add_error('target_amount', "Target amount must be a positive number.")
        if current_amount is not None and current_amount < 0:
            self.add_error('current_amount', "Current amount cannot be negative.")
            
        return cleaned_data


class GoalQuickUpdateForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = ['current_amount']
        widgets = {
            'current_amount': forms.NumberInput(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'placeholder': '0.00',
                'step': '0.01',
            }),
        }

    def clean_current_amount(self):
        current_amount = self.cleaned_data.get('current_amount')
        if current_amount is not None and current_amount < 0:
            raise forms.ValidationError("Saved amount cannot be negative.")
        return current_amount
