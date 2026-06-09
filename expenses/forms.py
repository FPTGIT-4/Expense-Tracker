from django import forms
from .models import Expense
from categories.models import Category
from accounts.models import Account

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['account', 'name', 'amount', 'date', 'category', 'description']
        widgets = {
            'account': forms.Select(attrs={
                'class': 'form-select bg-dark-custom text-white border-glass',
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'placeholder': 'Enter expense name (e.g. Lunch, Utilities bill)',
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0.01',
            }),
            'date': forms.DateInput(format='%Y-%m-%d', attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'type': 'date',
            }),
            'category': forms.Select(attrs={
                'class': 'form-select bg-dark-custom text-white border-glass',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'placeholder': 'Enter description details (optional)...',
                'rows': 3,
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            from django.utils import timezone
            self.fields['date'].initial = timezone.localdate()
        if user:
            from decimal import Decimal
            if not Account.objects.filter(user=user).exists():
                Account.objects.create(
                    user=user,
                    name='Cash',
                    account_type='Cash',
                    initial_balance=Decimal('0.00')
                )
            self.fields['category'].queryset = Category.objects.filter(user=user)
            self.fields['category'].empty_label = "Select a category (optional)"
            self.fields['account'].queryset = Account.objects.filter(user=user).exclude(status='CLOSED')
            self.fields['account'].empty_label = "Select an account"
            self.fields['account'].required = True

    def clean(self):
        cleaned_data = super().clean()
        account = cleaned_data.get('account')
        if account:
            if account.status == 'INACTIVE':
                self.add_error('account', "Cannot create transactions for an inactive account.")
            elif account.status == 'CLOSED':
                self.add_error('account', "Cannot create transactions for a closed account.")
        return cleaned_data
