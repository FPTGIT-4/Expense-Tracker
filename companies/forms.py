from django import forms
from .models import CompanyAccount, CompanyIncome, CompanyExpense
from categories.models import Category

class CompanyAccountForm(forms.ModelForm):
    class Meta:
        model = CompanyAccount
        fields = ['name', 'description', 'opening_balance', 'status', 'created_date']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'placeholder': 'Enter company name...',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'placeholder': 'Enter company description (optional)...',
                'rows': 3,
            }),
            'opening_balance': forms.NumberInput(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'placeholder': '0.00',
                'step': '0.01',
            }),
            'status': forms.Select(attrs={
                'class': 'form-select bg-dark-custom text-white border-glass',
            }),
            'created_date': forms.DateInput(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'type': 'date',
            }),
        }


class CompanyIncomeForm(forms.ModelForm):
    class Meta:
        model = CompanyIncome
        fields = ['company_account', 'amount', 'source', 'date', 'description']
        widgets = {
            'company_account': forms.Select(attrs={
                'class': 'form-select bg-dark-custom text-white border-glass',
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'placeholder': '0.00',
                'step': '0.01',
            }),
            'source': forms.TextInput(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'placeholder': 'Enter source (e.g. Invoice #102, Client Payment)...',
            }),
            'date': forms.DateInput(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'type': 'date',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'placeholder': 'Enter transaction details (optional)...',
                'rows': 3,
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['company_account'].queryset = CompanyAccount.objects.filter(user=user, status='ACTIVE')
            self.fields['company_account'].empty_label = "Select a Company Account"
            self.fields['company_account'].required = True


class CompanyExpenseForm(forms.ModelForm):
    class Meta:
        model = CompanyExpense
        fields = ['company_account', 'name', 'category', 'amount', 'date', 'description']
        widgets = {
            'company_account': forms.Select(attrs={
                'class': 'form-select bg-dark-custom text-white border-glass',
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'placeholder': 'Enter expense item (e.g. Office rent, Server hosting)...',
            }),
            'category': forms.Select(attrs={
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
            'description': forms.Textarea(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'placeholder': 'Enter transaction details (optional)...',
                'rows': 3,
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['company_account'].queryset = CompanyAccount.objects.filter(user=user, status='ACTIVE')
            self.fields['company_account'].empty_label = "Select a Company Account"
            self.fields['company_account'].required = True
            
            self.fields['category'].queryset = Category.objects.filter(user=user)
            self.fields['category'].empty_label = "Select a category (optional)"
            self.fields['category'].required = False
