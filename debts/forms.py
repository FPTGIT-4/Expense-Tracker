from django import forms
from django.db import models
from .models import Debt, Repayment

class DebtForm(forms.ModelForm):
    class Meta:
        model = Debt
        fields = ['person_name', 'debt_type', 'amount', 'date', 'due_date', 'notes']
        widgets = {
            'person_name': forms.TextInput(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'placeholder': 'Enter person\'s name...',
            }),
            'debt_type': forms.Select(attrs={
                'class': 'form-select bg-dark-custom text-white border-glass',
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'placeholder': '0.00',
                'step': '0.01',
            }),
            'date': forms.DateInput(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'type': 'date',
            }),
            'due_date': forms.DateInput(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'type': 'date',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'placeholder': 'Enter optional notes...',
                'rows': 3,
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount')
        date = cleaned_data.get('date')
        due_date = cleaned_data.get('due_date')

        if amount is not None and amount <= 0:
            self.add_error('amount', "Debt amount must be a positive number greater than zero.")
        if date and due_date and due_date < date:
            self.add_error('due_date', "Due date cannot be before the debt creation date.")

        return cleaned_data


class RepaymentForm(forms.ModelForm):
    class Meta:
        model = Repayment
        fields = ['amount', 'date', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'placeholder': '0.00',
                'step': '0.01',
            }),
            'date': forms.DateInput(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'type': 'date',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'placeholder': 'Enter payment notes (optional)...',
                'rows': 2,
            }),
        }

    def __init__(self, *args, **kwargs):
        self.debt = kwargs.pop('debt', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount')

        if amount is not None and amount <= 0:
            self.add_error('amount', "Payment amount must be greater than zero.")

        if amount is not None and self.debt:
            # If editing, exclude current instance amount from the total
            instance_pk = self.instance.pk if self.instance else None
            other_payments = self.debt.payments.exclude(pk=instance_pk)
            total_other_paid = other_payments.aggregate(total=models.Sum('amount'))['total'] or 0
            remaining = self.debt.amount - total_other_paid
            if amount > remaining:
                self.add_error('amount', f"Payment amount ({amount}) cannot exceed the remaining balance ({remaining}).")

        return cleaned_data
