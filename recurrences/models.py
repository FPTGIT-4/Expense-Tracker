from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
import datetime

from categories.models import Category
from accounts.models import Account
from companies.models import CompanyAccount
from income.models import Income
from expenses.models import Expense
from companies.models import CompanyIncome, CompanyExpense

def add_months(date_val, months):
    month = date_val.month - 1 + months
    year = date_val.year + month // 12
    month = month % 12 + 1
    day = min(date_val.day, [31,
        29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
        31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month-1])
    return datetime.date(year, month, day)

class RecurringTransaction(models.Model):
    TYPE_CHOICES = [
        ('Income', 'Recurring Income'),
        ('Expense', 'Recurring Expense'),
    ]

    FREQUENCY_CHOICES = [
        ('Daily', 'Daily'),
        ('Weekly', 'Weekly'),
        ('Monthly', 'Monthly'),
        ('Quarterly', 'Quarterly'),
        ('Yearly', 'Yearly'),
    ]

    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recurring_transactions')
    name = models.CharField(max_length=200)
    transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='recurring_transactions')
    account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name='recurring_transactions')
    company_account = models.ForeignKey(CompanyAccount, on_delete=models.SET_NULL, null=True, blank=True, related_name='recurring_transactions')
    frequency = models.CharField(max_length=15, choices=FREQUENCY_CHOICES)
    start_date = models.DateField(default=timezone.localdate)
    end_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.frequency} {self.transaction_type} ({self.amount})"

    @property
    def monthly_equivalent(self):
        amt = self.amount
        if self.frequency == 'Daily':
            return amt * Decimal('30')
        elif self.frequency == 'Weekly':
            return amt * Decimal('4.33')
        elif self.frequency == 'Monthly':
            return amt
        elif self.frequency == 'Quarterly':
            return amt / Decimal('3')
        elif self.frequency == 'Yearly':
            return amt / Decimal('12')
        return Decimal('0.00')

    @property
    def next_due_date(self):
        if self.status == 'Inactive':
            return None
        
        today = timezone.localdate()
        if self.start_date > today:
            return self.start_date

        curr = self.start_date
        if self.frequency == 'Daily':
            delta = (today - self.start_date).days
            if delta > 0:
                curr += datetime.timedelta(days=delta)
            while curr < today or self.occurrences.filter(occurrence_date=curr).exists():
                curr += datetime.timedelta(days=1)
        elif self.frequency == 'Weekly':
            delta_weeks = (today - self.start_date).days // 7
            if delta_weeks > 0:
                curr += datetime.timedelta(weeks=delta_weeks)
            while curr < today or self.occurrences.filter(occurrence_date=curr).exists():
                curr += datetime.timedelta(weeks=1)
        elif self.frequency == 'Monthly':
            delta_months = (today.year - self.start_date.year) * 12 + (today.month - self.start_date.month)
            if delta_months > 0:
                curr = add_months(self.start_date, delta_months)
            while curr < today or self.occurrences.filter(occurrence_date=curr).exists():
                delta_months += 1
                curr = add_months(self.start_date, delta_months)
        elif self.frequency == 'Quarterly':
            delta_months = (today.year - self.start_date.year) * 12 + (today.month - self.start_date.month)
            quarters = delta_months // 3
            if quarters > 0:
                curr = add_months(self.start_date, quarters * 3)
            while curr < today or self.occurrences.filter(occurrence_date=curr).exists():
                quarters += 1
                curr = add_months(self.start_date, quarters * 3)
        elif self.frequency == 'Yearly':
            years = today.year - self.start_date.year
            if years > 0:
                curr = add_months(self.start_date, years * 12)
            while curr < today or self.occurrences.filter(occurrence_date=curr).exists():
                years += 1
                curr = add_months(self.start_date, years * 12)

        if self.end_date and curr > self.end_date:
            return None
        return curr

    def clean(self):
        super().clean()
        if self.amount is not None and self.amount <= 0:
            raise ValidationError({'amount': "Amount must be a positive number greater than zero."})
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError({'end_date': "End date cannot be before the start date."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class GeneratedOccurrence(models.Model):
    recurring_transaction = models.ForeignKey(RecurringTransaction, on_delete=models.CASCADE, related_name='occurrences')
    occurrence_date = models.DateField()
    income = models.ForeignKey(Income, on_delete=models.SET_NULL, null=True, blank=True)
    expense = models.ForeignKey(Expense, on_delete=models.SET_NULL, null=True, blank=True)
    company_income = models.ForeignKey(CompanyIncome, on_delete=models.SET_NULL, null=True, blank=True)
    company_expense = models.ForeignKey(CompanyExpense, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-occurrence_date']
        unique_together = ('recurring_transaction', 'occurrence_date')

    def __str__(self):
        return f"Generated on {self.occurrence_date} for {self.recurring_transaction.name}"
