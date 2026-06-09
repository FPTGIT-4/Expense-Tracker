from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.db.models import Sum
from decimal import Decimal
import calendar

from categories.models import Category

class Budget(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='budgets')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='budgets')
    budget_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    month = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    year = models.IntegerField(
        validators=[MinValueValidator(2000), MaxValueValidator(2100)]
    )
    notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-year', '-month', 'category__name']
        unique_together = ('category', 'month', 'year')

    def __str__(self):
        return f"{self.category.name} Budget - {self.month}/{self.year} ({self.user.username})"

    def clean(self):
        super().clean()
        if self.budget_amount is not None and self.budget_amount <= 0:
            raise ValidationError({'budget_amount': 'Budget amount must be greater than zero.'})
        
        # Verify that category user matches budget user (safeguard for forms/admin validation)
        try:
            if self.category_id and hasattr(self, 'user') and self.user_id:
                if self.category.user != self.user:
                    raise ValidationError({'category': 'Selected category does not belong to this user.'})
        except (AttributeError, User.DoesNotExist, Category.DoesNotExist):
            pass

        # Ensure no duplicates (only check for new instances or if unique fields changed)
        if self.category_id and self.month and self.year:
            duplicate_exists = Budget.objects.filter(
                category_id=self.category_id,
                month=self.month,
                year=self.year
            ).exclude(pk=self.pk).exists()

            if duplicate_exists:
                month_name = calendar.month_name[self.month]
                raise ValidationError(
                    f"A budget for category '{self.category.name}' in {month_name} {self.year} already exists."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    # --- Calculations Properties ---

    @property
    def total_spent(self):
        """Sum of all expenses in that category during the selected month/year."""
        from expenses.models import Expense
        total = Expense.objects.filter(
            user=self.user,
            category=self.category,
            date__month=self.month,
            date__year=self.year
        ).aggregate(total=Sum('amount'))['total']
        return total or Decimal('0.00')

    @property
    def remaining_budget(self):
        """Remaining = Budget Amount - Total Spent"""
        return self.budget_amount - self.total_spent

    @property
    def usage_percentage(self):
        """Usage % = (Spent / Budget Amount) * 100"""
        if self.budget_amount > 0:
            spent = self.total_spent
            pct = (spent / self.budget_amount) * 100
            return float(pct)
        return 0.0

    @property
    def status_text(self):
        """
        Status text for UI badge: Exceeded, Warning, or Normal.
        Warning is active only if enable_budget_alerts is True.
        """
        try:
            settings = self.user.settings
            threshold = settings.budget_threshold
            enable_alerts = settings.enable_budget_alerts
        except Exception:
            threshold = 80
            enable_alerts = True
            
        pct = self.usage_percentage
        if pct >= 100:
            return 'Exceeded'
        elif enable_alerts and pct >= threshold:
            return 'Warning'
        else:
            return 'Normal'

    @property
    def status_class(self):
        """
        Bootstrap class corresponding to the budget status.
        Normal -> success (Green)
        Warning -> warning (Yellow)
        Exceeded -> danger (Red)
        """
        status = self.status_text
        if status == 'Exceeded':
            return 'danger'
        elif status == 'Warning':
            return 'warning'
        else:
            return 'success'

    # --- Dashboard Preparation ---

    @classmethod
    def get_user_budgets(cls, user, month=None, year=None, active_only=True):
        qs = cls.objects.filter(user=user)
        if active_only:
            qs = qs.filter(is_active=True)
        if month:
            qs = qs.filter(month=month)
        if year:
            qs = qs.filter(year=year)
        return qs

    @classmethod
    def get_total_budgets(cls, user, month=None, year=None):
        return cls.get_user_budgets(user, month, year).count()

    @classmethod
    def get_total_budget_amount(cls, user, month=None, year=None):
        total = cls.get_user_budgets(user, month, year).aggregate(total=Sum('budget_amount'))['total']
        return total or Decimal('0.00')

    @classmethod
    def get_total_spent(cls, user, month=None, year=None):
        budgets = cls.get_user_budgets(user, month, year)
        category_ids = budgets.values_list('category_id', flat=True)
        
        if month and year:
            from expenses.models import Expense
            total = Expense.objects.filter(
                user=user,
                category_id__in=category_ids,
                date__month=month,
                date__year=year
            ).aggregate(total=Sum('amount'))['total']
            return total or Decimal('0.00')
        else:
            # Fallback if no specific month/year is provided
            return sum((b.total_spent for b in budgets), Decimal('0.00'))

    @classmethod
    def get_total_remaining(cls, user, month=None, year=None):
        # Remaining sum calculated overall
        return cls.get_total_budget_amount(user, month, year) - cls.get_total_spent(user, month, year)

    # --- Report Preparation ---

    @classmethod
    def get_monthly_budget_summary(cls, user, year):
        """Returns monthly budgets overview for a given year."""
        summary = []
        for m in range(1, 13):
            budgets = cls.get_user_budgets(user, month=m, year=year)
            if not budgets.exists():
                continue
            
            total_budget = sum((b.budget_amount for b in budgets), Decimal('0.00'))
            total_spent = sum((b.total_spent for b in budgets), Decimal('0.00'))
            total_remaining = total_budget - total_spent
            usage_pct = float((total_spent / total_budget) * 100) if total_budget > 0 else 0.0
            
            summary.append({
                'month': m,
                'month_name': calendar.month_name[m],
                'total_budget': total_budget,
                'total_spent': total_spent,
                'total_remaining': total_remaining,
                'usage_percentage': usage_pct,
            })
        return summary

    @classmethod
    def get_category_budget_summary(cls, user, month, year):
        """Returns details of all budgets for a given month and year."""
        budgets = cls.get_user_budgets(user, month=month, year=year)
        summary = []
        for b in budgets:
            summary.append({
                'budget_id': b.id,
                'category': b.category,
                'budget_amount': b.budget_amount,
                'total_spent': b.total_spent,
                'remaining_budget': b.remaining_budget,
                'usage_percentage': b.usage_percentage,
                'status_class': b.status_class,
                'status_text': b.status_text,
            })
        return summary

    @classmethod
    def get_budget_vs_actual_analysis(cls, user, month, year):
        """Returns high-level analysis of actual vs budgeted values."""
        details = cls.get_category_budget_summary(user, month, year)
        
        total_budget = sum((d['budget_amount'] for d in details), Decimal('0.00'))
        total_spent = sum((d['total_spent'] for d in details), Decimal('0.00'))
        total_remaining = total_budget - total_spent
        overall_usage = float((total_spent / total_budget) * 100) if total_budget > 0 else 0.0
        
        exceeded_count = 0
        warning_count = 0
        on_track_count = 0
        
        try:
            settings = user.settings
            threshold = settings.budget_threshold
            enable_alerts = settings.enable_budget_alerts
        except Exception:
            threshold = 80
            enable_alerts = True
        
        for d in details:
            if d['usage_percentage'] >= 100:
                exceeded_count += 1
            elif enable_alerts and d['usage_percentage'] >= threshold:
                warning_count += 1
            else:
                on_track_count += 1
                
        return {
            'total_budget_amount': total_budget,
            'total_spent': total_spent,
            'total_remaining': total_remaining,
            'overall_usage_percentage': overall_usage,
            'exceeded_categories_count': exceeded_count,
            'warning_categories_count': warning_count,
            'on_track_categories_count': on_track_count,
            'details': details,
        }


from django.utils import timezone

def get_warning_budgets(user, month=None, year=None):
    """
    Returns a list of active Budget objects that have reached the warning threshold
    but have not exceeded 100%, provided that budget alerts are enabled.
    """
    if month is None or year is None:
        today = timezone.localdate()
        if month is None:
            month = today.month
        if year is None:
            year = today.year

    try:
        settings = user.settings
        enable_alerts = settings.enable_budget_alerts
        threshold = settings.budget_threshold
    except Exception:
        enable_alerts = True
        threshold = 80

    if not enable_alerts:
        return []

    active_budgets = Budget.objects.filter(user=user, is_active=True, month=month, year=year)
    warning_budgets = []
    for b in active_budgets:
        pct = b.usage_percentage
        if threshold <= pct < 100:
            warning_budgets.append(b)
    return warning_budgets


def get_exceeded_budgets(user, month=None, year=None):
    """
    Returns a list of active Budget objects that have exceeded 100% of their budget,
    provided that budget alerts are enabled.
    """
    if month is None or year is None:
        today = timezone.localdate()
        if month is None:
            month = today.month
        if year is None:
            year = today.year

    try:
        settings = user.settings
        enable_alerts = settings.enable_budget_alerts
    except Exception:
        enable_alerts = True

    if not enable_alerts:
        return []

    active_budgets = Budget.objects.filter(user=user, is_active=True, month=month, year=year)
    exceeded_budgets = []
    for b in active_budgets:
        if b.usage_percentage >= 100:
            exceeded_budgets.append(b)
    return exceeded_budgets


def get_budget_alerts(user, month=None, year=None):
    """
    Returns a list of alerts (both warnings and exceeded) as structured dictionaries.
    Each alert contains key data and a formatted message.
    """
    if month is None or year is None:
        today = timezone.localdate()
        if month is None:
            month = today.month
        if year is None:
            year = today.year

    try:
        settings = user.settings
        enable_alerts = settings.enable_budget_alerts
    except Exception:
        enable_alerts = True

    if not enable_alerts:
        return []

    try:
        currency_symbol = user.settings.currency
    except Exception:
        currency_symbol = '₹'

    alerts = []

    # 1. Exceeded Budgets (sorted first)
    exceeded = get_exceeded_budgets(user, month, year)
    for b in exceeded:
        exceeded_amount = b.total_spent - b.budget_amount
        if exceeded_amount % 1 == 0:
            exceeded_str = f"{int(exceeded_amount)}"
        else:
            exceeded_str = f"{exceeded_amount:.2f}"
            
        alerts.append({
            'type': 'exceeded',
            'budget': b,
            'message': f"🚨 {b.category.name} Budget exceeded by {currency_symbol}{exceeded_str}.",
            'usage_percentage': b.usage_percentage,
            'spent': b.total_spent,
            'amount': b.budget_amount,
            'exceeded_by': exceeded_amount,
            'exceeded_by_str': exceeded_str,
            'remaining': b.remaining_budget,
            'remaining_str': f"-{exceeded_str}",
        })

    # 2. Warning Budgets (sorted second)
    warnings = get_warning_budgets(user, month, year)
    for b in warnings:
        remaining_amount = b.remaining_budget
        if remaining_amount % 1 == 0:
            remaining_str = f"{int(remaining_amount)}"
        else:
            remaining_str = f"{remaining_amount:.2f}"

        alerts.append({
            'type': 'warning',
            'budget': b,
            'message': f"⚠ {b.category.name} Budget has reached {int(round(b.usage_percentage))}% of its allocated budget.",
            'usage_percentage': b.usage_percentage,
            'spent': b.total_spent,
            'amount': b.budget_amount,
            'remaining': remaining_amount,
            'remaining_str': remaining_str,
        })

    return alerts


def get_budget_alert_count(user, month=None, year=None):
    """
    Returns the total count of warning alerts + exceeded alerts.
    """
    warnings_count = len(get_warning_budgets(user, month, year))
    exceeded_count = len(get_exceeded_budgets(user, month, year))
    return warnings_count + exceeded_count
