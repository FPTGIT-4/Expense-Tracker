from django import forms
from .models import Account, AccountTransfer, UserSettings


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
            'transfer_date': forms.DateInput(format='%Y-%m-%d', attrs={
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
        self.user = user
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            from django.utils import timezone
            self.fields['transfer_date'].initial = timezone.localdate()
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
                try:
                    currency_symbol = self.user.settings.currency if self.user else '₹'
                except Exception:
                    currency_symbol = '₹'
                self.add_error('amount', f"Insufficient funds in {from_account.name}. Current balance: {currency_symbol}{from_account.current_balance:.2f}")

        return cleaned_data


class UserSettingsForm(forms.ModelForm):
    class Meta:
        model = UserSettings
        fields = [
            'currency',
            'budget_threshold',
            'enable_budget_alerts',
            # Low-balance alert settings
            'low_balance_alerts',
            'low_balance_show_navbar_badge',
            'low_balance_show_dashboard_banner',
            'low_balance_show_dashboard_panel',
            'low_balance_alert_scope',
            'low_balance_default_minimum',
            # Appearance
            'dark_mode',
        ]
        widgets = {
            'currency': forms.Select(attrs={
                'class': 'form-select bg-dark-custom text-white border-glass',
            }),
            'budget_threshold': forms.NumberInput(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'min': '1',
                'max': '100',
                'step': '1',
                'placeholder': '80',
            }),
            'enable_budget_alerts': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'role': 'switch',
            }),
            'low_balance_alerts': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'role': 'switch',
            }),
            'low_balance_show_navbar_badge': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'role': 'switch',
            }),
            'low_balance_show_dashboard_banner': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'role': 'switch',
            }),
            'low_balance_show_dashboard_panel': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'role': 'switch',
            }),
            'low_balance_alert_scope': forms.Select(attrs={
                'class': 'form-select bg-dark-custom text-white border-glass',
            }),
            'low_balance_default_minimum': forms.NumberInput(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'placeholder': '0.00 (0 = disabled)',
                'step': '0.01',
                'min': '0',
            }),
            'dark_mode': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'role': 'switch',
                'id': 'id_dark_mode',
            }),
        }


