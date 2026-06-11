from django import forms
from .models import Expense
from categories.models import Category, Label
from accounts.models import Account

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['account', 'name', 'amount', 'date', 'category', 'labels', 'description']
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
            
            self.fields['category'].queryset = Category.objects.filter(user=user)
            self.fields['category'].choices = [(c.pk, str(c)) for c in user._categories_cache]
            self.fields['category'].empty_label = "Select a category (optional)"
            
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
