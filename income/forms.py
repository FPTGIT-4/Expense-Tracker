from django import forms
from .models import Income
from accounts.models import Account
from categories.models import Label

class IncomeForm(forms.ModelForm):
    class Meta:
        model = Income
        fields = ['account', 'amount', 'source', 'date', 'labels', 'description']
        widgets = {
            'account': forms.Select(attrs={
                'class': 'form-select bg-dark-custom text-white border-glass',
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0.01',
            }),
            'source': forms.Select(attrs={
                'class': 'form-select bg-dark-custom text-white border-glass',
            }),
            'date': forms.DateInput(format='%Y-%m-%d', attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'type': 'date',
            }),
            'labels': forms.CheckboxSelectMultiple(attrs={
                'class': 'form-check-input',
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
            from accounts.context_processors import prefill_user_caches
            prefill_user_caches(user)
            
            self.fields['labels'].queryset = Label.objects.filter(user=user)
            self.fields['labels'].choices = [(l.pk, str(l)) for l in user._labels_cache]
            self.fields['labels'].required = False
            
            self.fields['account'].queryset = Account.objects.filter(user=user).exclude(status='CLOSED')
            self.fields['account'].choices = [(a.pk, str(a)) for a in user._active_accounts_cache]
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
