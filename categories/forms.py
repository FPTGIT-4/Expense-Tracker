from django import forms
from .models import Category, Label

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'placeholder': 'Enter category name (e.g. Food, Utilities)',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'placeholder': 'Enter category description (optional)...',
                'rows': 3,
            }),
        }


class LabelForm(forms.ModelForm):
    class Meta:
        model = Label
        fields = ['name', 'color']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'placeholder': 'Enter label name (e.g. Tax-deductible, Reimbursement)',
            }),
            'color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'form-control bg-dark-custom border-glass',
                'style': 'width: 80px; height: 42px; padding: 4px; cursor: pointer;',
            }),
        }

