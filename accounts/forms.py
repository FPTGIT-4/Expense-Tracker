from django import forms
from .models import Account, UserSettings


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

    def clean_minimum_balance(self):
        from decimal import Decimal
        minimum_balance = self.cleaned_data.get('minimum_balance')
        if minimum_balance is None:
            return Decimal('0.00')
        if minimum_balance < 0:
            raise forms.ValidationError("Low balance threshold cannot be negative.")
        return minimum_balance

    def clean(self):
        cleaned_data = super().clean()
        self.instance._explicit_threshold_edit = True
        minimum_balance = cleaned_data.get('minimum_balance')
        initial_balance = cleaned_data.get('initial_balance')

        if minimum_balance is not None and initial_balance is not None:
            if minimum_balance > initial_balance:
                self.add_error('minimum_balance', "Low balance threshold cannot be greater than the opening balance.")
        return cleaned_data

    def save(self, commit=True):
        self.instance._explicit_threshold_edit = True
        return super().save(commit=commit)


class UserSettingsForm(forms.ModelForm):
    class Meta:
        model = UserSettings
        fields = ['currency']
        widgets = {
            'currency': forms.Select(attrs={
                'class': 'form-select bg-dark-custom text-white border-glass',
            }),
        }
