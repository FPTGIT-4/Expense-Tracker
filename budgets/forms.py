from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal
import calendar
import datetime

from .models import Budget
from categories.models import Category

class BudgetForm(forms.ModelForm):
    MONTH_CHOICES = [(i, calendar.month_name[i]) for i in range(1, 13)]

    month = forms.ChoiceField(
        choices=MONTH_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select bg-dark-custom text-white border-glass',
        })
    )

    class Meta:
        model = Budget
        fields = ['category', 'budget_amount', 'month', 'year', 'notes', 'is_active']
        widgets = {
            'category': forms.Select(attrs={
                'class': 'form-select bg-dark-custom text-white border-glass',
            }),
            'budget_amount': forms.NumberInput(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0.01',
            }),
            'year': forms.NumberInput(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'placeholder': 'YYYY',
                'min': '2000',
                'max': '2100',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'placeholder': 'Enter budget notes (optional)...',
                'rows': 3,
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Default month and year to current if new instance
        if not self.instance.pk:
            now = datetime.datetime.now()
            self.fields['month'].initial = now.month
            self.fields['year'].initial = now.year

        if user:
            from accounts.context_processors import prefill_user_caches
            prefill_user_caches(user)
            
            self.fields['category'].queryset = Category.objects.filter(user=user)
            self.fields['category'].choices = [(c.pk, str(c)) for c in user._categories_cache]
            self.fields['category'].empty_label = "Select a category"
            self.fields['category'].required = True

    def clean_month(self):
        # Cast string choice back to integer
        return int(self.cleaned_data['month'])

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')
        month = cleaned_data.get('month')
        year = cleaned_data.get('year')
        budget_amount = cleaned_data.get('budget_amount')

        # Check budget_amount is positive
        if budget_amount is not None and budget_amount <= 0:
            self.add_error('budget_amount', 'Budget amount must be greater than zero.')

        # Ensure month is cast to int
        if month is not None:
            try:
                month = int(month)
            except (ValueError, TypeError):
                pass

        # Check unique constraint
        if category and month and year:
            duplicate_exists = Budget.objects.filter(
                category=category,
                month=month,
                year=year
            ).exclude(pk=self.instance.pk).exists()
            
            if duplicate_exists:
                month_name = calendar.month_name[month]
                error_msg = f"A budget for category '{category.name}' in {month_name} {year} already exists."
                self.add_error('category', error_msg)
                self.add_error('month', "Duplicate budget detected.")
                self.add_error('year', "Duplicate budget detected.")
                
        return cleaned_data
