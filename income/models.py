from django.db import models
from django.contrib.auth.models import User
from categories.models import Label

class Income(models.Model):
    SOURCE_CHOICES = [
        ('Salary', 'Salary'),
        ('Business', 'Business'),
        ('Freelancing', 'Freelancing'),
        ('Interest', 'Interest'),
        ('Gift', 'Gift'),
        ('Other', 'Other'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='incomes')
    account = models.ForeignKey('accounts.Account', on_delete=models.CASCADE, related_name='incomes', null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES)
    date = models.DateField()
    description = models.TextField(blank=True, null=True)
    labels = models.ManyToManyField(Label, blank=True, related_name='incomes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def save(self, *args, **kwargs):
        if not self.account_id:
            from accounts.models import Account
            from decimal import Decimal
            account, _ = Account.objects.get_or_create(
                user=self.user,
                account_type='Cash',
                defaults={'name': 'Cash', 'initial_balance': Decimal('0.00')}
            )
            self.account = account
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.source} (${self.amount}) on {self.date}"
