from django import forms
from .models import Account, AccountTransfer

class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['name', 'account_type', 'initial_balance', 'minimum_balance', 'status', 'notes']
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
            'minimum_balance': forms.NumberInput(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'placeholder': '0.00 (optional — leave 0 to disable alert)',
                'step': '0.01',
                'min': '0',
            }),
            'status': forms.Select(attrs={
                'class': 'form-select bg-dark-custom text-white border-glass',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'placeholder': 'Additional account information',
                'rows': 3,
            }),
        }

class TransferForm(forms.ModelForm):
    class Meta:
        model = AccountTransfer
        fields = ['from_account', 'to_account', 'amount', 'transfer_date', 'note']
        widgets = {
            'from_account': forms.Select(attrs={
                'class': 'form-select bg-dark-custom text-white border-glass',
            }),
            'to_account': forms.Select(attrs={
                'class': 'form-select bg-dark-custom text-white border-glass',
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0.01',
            }),
            'transfer_date': forms.DateInput(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'type': 'date',
            }),
            'note': forms.Textarea(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'placeholder': 'Optional note...',
                'rows': 3,
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['from_account'].queryset = Account.objects.filter(user=user).exclude(status='CLOSED')
            self.fields['to_account'].queryset = Account.objects.filter(user=user).exclude(status='CLOSED')

    def clean(self):
        cleaned_data = super().clean()
        from_account = cleaned_data.get('from_account')
        amount = cleaned_data.get('amount')

        # Insufficient funds check
        if from_account and amount is not None and amount > 0:
            if from_account.current_balance < amount:
                self.add_error('amount', f"Insufficient funds in {from_account.name}. Current balance: ₹{from_account.current_balance:.2f}")

        return cleaned_data
