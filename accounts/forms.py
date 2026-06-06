from django import forms
from .models import Account

class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['name', 'account_type', 'initial_balance']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'placeholder': 'e.g. My Bank Account, Pocket Cash',
            }),
            'account_type': forms.Select(attrs={
                'class': 'form-select bg-dark-custom text-white border-glass',
            }),
            'initial_balance': forms.NumberInput(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'placeholder': '0.00',
                'step': '0.01',
            }),
        }
