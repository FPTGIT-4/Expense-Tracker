from django.db import models
from django.contrib.auth.models import User


class Category(models.Model):
    TYPE_EXPENSE = 'expense'
    TYPE_INCOME  = 'income'

    TYPE_CHOICES = [
        (TYPE_EXPENSE, 'Expense'),
        (TYPE_INCOME,  'Income'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    category_type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        default=TYPE_EXPENSE,
        verbose_name='Type',
    )
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Categories'
        unique_together = ('user', 'name', 'category_type')

    def __str__(self):
        return self.name

    @property
    def type_label(self):
        return dict(self.TYPE_CHOICES).get(self.category_type, self.category_type)


class SubCategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Subcategories'
        unique_together = ('category', 'name')

    def __str__(self):
        return self.name
