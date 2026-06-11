from django import forms
from .models import RecurringTransaction
from categories.models import Category
from accounts.models import Account
from companies.models import CompanyAccount

class RecurringTransactionForm(forms.ModelForm):
    class Meta:
        model = RecurringTransaction
        fields = [
            'name', 'transaction_type', 'amount', 'category', 
            'account', 'company_account', 'frequency', 
            'start_date', 'end_date', 'notes', 'status'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'placeholder': 'Enter transaction name (e.g. Salary, Rent, Subscription)...',
            }),
            'transaction_type': forms.Select(attrs={
                'class': 'form-select bg-dark-custom text-white border-glass',
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'placeholder': '0.00',
                'step': '0.01',
            }),
            'category': forms.Select(attrs={
                'class': 'form-select bg-dark-custom text-white border-glass',
            }),
            'account': forms.Select(attrs={
                'class': 'form-select bg-dark-custom text-white border-glass',
            }),
            'company_account': forms.Select(attrs={
                'class': 'form-select bg-dark-custom text-white border-glass',
            }),
            'frequency': forms.Select(attrs={
                'class': 'form-select bg-dark-custom text-white border-glass',
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'type': 'date',
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'type': 'date',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'placeholder': 'Enter optional notes...',
                'rows': 3,
            }),
            'status': forms.Select(attrs={
                'class': 'form-select bg-dark-custom text-white border-glass',
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Make account and company_account optional in the HTML forms
        self.fields['account'].required = False
        self.fields['company_account'].required = False
        
        if user:
            self.fields['category'].queryset = Category.objects.filter(user=user)
            self.fields['account'].queryset = Account.objects.filter(user=user)
            self.fields['company_account'].queryset = CompanyAccount.objects.filter(user=user)

    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if amount is not None and amount <= 0:
            self.add_error('amount', "Amount must be a positive number greater than zero.")
        if start_date and end_date and end_date < start_date:
            self.add_error('end_date', "End date cannot be before the start date.")

        return cleaned_data
