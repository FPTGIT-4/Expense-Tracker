from django import forms
from .models import Category, SubCategory


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'category_type', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'placeholder': 'Enter category name (e.g. Food, Salary)',
            }),
            'category_type': forms.RadioSelect(),   # rendered manually in template
            'description': forms.Textarea(attrs={
                'class': 'form-control bg-dark-custom text-white border-glass',
                'placeholder': 'Enter category description (optional)...',
                'rows': 3,
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        self.user = user
        super().__init__(*args, **kwargs)
        # Restrict to only Expense / Income (no "Both")
        self.fields['category_type'].choices = Category.TYPE_CHOICES

    def save(self, commit=True):
        category = super().save(commit=False)
        if commit:
            category.save()
        return category

    def clean_name(self):
        name = self.cleaned_data.get('name')
        category_type = self.data.get('category_type', '')
        user = getattr(self, 'user', None) or (
            self.instance.user if self.instance and hasattr(self.instance, 'user') else None
        )
        if user and category_type:
            qs = Category.objects.filter(user=user, name=name, category_type=category_type)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                type_label = dict(Category.TYPE_CHOICES).get(category_type, category_type)
                raise forms.ValidationError(
                    f'You already have an "{type_label}" category with this name.'
                )
        return name
