from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from decimal import Decimal
import datetime

from categories.models import Category
from expenses.models import Expense
from .models import Budget
from .forms import BudgetForm

class BudgetModelAndHelperTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.category = Category.objects.create(user=self.user, name='Food')
        
    def test_budget_amount_greater_than_zero(self):
        # Budget amount must be greater than 0
        budget = Budget(
            user=self.user,
            category=self.category,
            budget_amount=Decimal('0.00'),
            month=6,
            year=2026
        )
        with self.assertRaises(ValidationError):
            budget.clean()

    def test_budget_unique_together_constraint(self):
        # Create initial budget
        Budget.objects.create(
            user=self.user,
            category=self.category,
            budget_amount=Decimal('500.00'),
            month=6,
            year=2026
        )
        # Attempt duplicate budget
        duplicate = Budget(
            user=self.user,
            category=self.category,
            budget_amount=Decimal('300.00'),
            month=6,
            year=2026
        )
        with self.assertRaises(ValidationError):
            duplicate.clean()

    def test_budget_calculations_properties(self):
        from accounts.models import UserSettings
        settings, _ = UserSettings.objects.get_or_create(user=self.user)
        settings.budget_threshold = 80
        settings.save()

        # Create active budget
        budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            budget_amount=Decimal('100.00'),
            month=6,
            year=2026
        )
        
        # Create expenses
        Expense.objects.create(
            user=self.user,
            name='Lunch',
            amount=Decimal('35.50'),
            category=self.category,
            date=datetime.date(2026, 6, 1)
        )
        Expense.objects.create(
            user=self.user,
            name='Dinner',
            amount=Decimal('40.00'),
            category=self.category,
            date=datetime.date(2026, 6, 2)
        )
        # Expense in different month
        Expense.objects.create(
            user=self.user,
            name='July lunch',
            amount=Decimal('20.00'),
            category=self.category,
            date=datetime.date(2026, 7, 1)
        )
        
        # Test calculations
        self.assertEqual(budget.total_spent, Decimal('75.50'))
        self.assertEqual(budget.remaining_budget, Decimal('24.50'))
        self.assertEqual(budget.usage_percentage, 75.5)
        self.assertEqual(budget.status_class, 'success')
        self.assertEqual(budget.status_text, 'Normal')
        
        # Over-spent test
        Expense.objects.create(
            user=self.user,
            name='Snack',
            amount=Decimal('30.00'),
            category=self.category,
            date=datetime.date(2026, 6, 3)
        )
        self.assertEqual(budget.total_spent, Decimal('105.50'))
        self.assertEqual(budget.remaining_budget, Decimal('-5.50'))
        self.assertEqual(budget.usage_percentage, 105.5)
        self.assertEqual(budget.status_class, 'danger')
        self.assertEqual(budget.status_text, 'Exceeded')

    def test_dashboard_reusable_methods(self):
        # Create multiple budgets
        b1 = Budget.objects.create(
            user=self.user,
            category=self.category,
            budget_amount=Decimal('200.00'),
            month=6,
            year=2026
        )
        cat2 = Category.objects.create(user=self.user, name='Bills')
        b2 = Budget.objects.create(
            user=self.user,
            category=cat2,
            budget_amount=Decimal('300.00'),
            month=6,
            year=2026
        )
        
        # Test Dashboard Helpers
        self.assertEqual(Budget.get_total_budgets(self.user, month=6, year=2026), 2)
        self.assertEqual(Budget.get_total_budget_amount(self.user, month=6, year=2026), Decimal('500.00'))
        
        # Create expenses
        Expense.objects.create(
            user=self.user,
            name='Groceries',
            amount=Decimal('50.00'),
            category=self.category,
            date=datetime.date(2026, 6, 5)
        )
        Expense.objects.create(
            user=self.user,
            name='Electricity',
            amount=Decimal('150.00'),
            category=cat2,
            date=datetime.date(2026, 6, 10)
        )
        
        self.assertEqual(Budget.get_total_spent(self.user, month=6, year=2026), Decimal('200.00'))
        self.assertEqual(Budget.get_total_remaining(self.user, month=6, year=2026), Decimal('300.00'))

    def test_report_reusable_methods(self):
        from accounts.models import UserSettings
        settings, _ = UserSettings.objects.get_or_create(user=self.user)
        settings.budget_threshold = 80
        settings.save()

        Budget.objects.create(
            user=self.user,
            category=self.category,
            budget_amount=Decimal('500.00'),
            month=6,
            year=2026
        )
        
        # Test Monthly summary
        summary = Budget.get_monthly_budget_summary(self.user, year=2026)
        self.assertEqual(len(summary), 1)
        self.assertEqual(summary[0]['month'], 6)
        self.assertEqual(summary[0]['total_budget'], Decimal('500.00'))
        
        # Test Category budget summary
        cat_summary = Budget.get_category_budget_summary(self.user, month=6, year=2026)
        self.assertEqual(len(cat_summary), 1)
        self.assertEqual(cat_summary[0]['budget_amount'], Decimal('500.00'))
        
        # Test vs Actual analysis
        analysis = Budget.get_budget_vs_actual_analysis(self.user, month=6, year=2026)
        self.assertEqual(analysis['total_budget_amount'], Decimal('500.00'))
        self.assertEqual(analysis['on_track_categories_count'], 1)


class BudgetFormAndCRUDViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='viewsuser', password='password123')
        self.other_user = User.objects.create_user(username='otheruser', password='password123')
        self.category = Category.objects.create(user=self.user, name='Housing')
        self.other_category = Category.objects.create(user=self.other_user, name='Business')
        
        self.budget = Budget.objects.create(
            user=self.user,
            category=self.category,
            budget_amount=Decimal('1000.00'),
            month=8,
            year=2026
        )

    def test_budget_form_filters_user_categories(self):
        form = BudgetForm(user=self.user)
        queryset = form.fields['category'].queryset
        self.assertIn(self.category, queryset)
        self.assertNotIn(self.other_category, queryset)

    def test_budget_form_validation(self):
        # Test positive validation
        form_data = {
            'category': self.category.pk,
            'budget_amount': '0.00', # invalid <= 0
            'month': '8',
            'year': '2026',
            'notes': '',
            'is_active': True
        }
        form = BudgetForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('budget_amount', form.errors)
        
        # Test duplicate validation
        form_data['budget_amount'] = '500.00'
        form = BudgetForm(data=form_data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('category', form.errors)
        self.assertIn('month', form.errors)

    def test_list_view_authentication_and_filtering(self):
        # Redirect anonymous
        response = self.client.get(reverse('budget-list'))
        self.assertRedirects(response, f"/accounts/login/?next={reverse('budget-list')}")
        
        # Logged in
        self.client.force_login(self.user)
        response = self.client.get(reverse('budget-list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'budgets/budget_list.html')
        self.assertContains(response, 'Housing')
        
        # Other user's budget should not show up
        other_budget = Budget.objects.create(
            user=self.other_user,
            category=self.other_category,
            budget_amount=Decimal('200.00'),
            month=8,
            year=2026
        )
        response = self.client.get(reverse('budget-list'))
        self.assertNotIn(other_budget, response.context['budgets'])

    def test_budget_search(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('budget-list') + '?search=Hous')
        self.assertContains(response, 'Housing')
        
        response = self.client.get(reverse('budget-list') + '?search=Food')
        self.assertNotIn(self.budget, response.context['budgets'])

    def test_budget_detail_view(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('budget-detail', args=[self.budget.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'budgets/budget_detail.html')
        self.assertContains(response, 'Housing')
        self.assertContains(response, '1000.00')

        # Try accessing other user's budget detail (returns 404)
        other_budget = Budget.objects.create(
            user=self.other_user,
            category=self.other_category,
            budget_amount=Decimal('200.00'),
            month=8,
            year=2026
        )
        response = self.client.get(reverse('budget-detail', args=[other_budget.pk]))
        self.assertEqual(response.status_code, 404)

    def test_budget_create_view(self):
        self.client.force_login(self.user)
        form_data = {
            'category': self.category.pk,
            'budget_amount': '150.00',
            'month': '9',
            'year': '2026',
            'notes': 'test notes',
            'is_active': True
        }
        response = self.client.post(reverse('budget-add'), data=form_data)
        self.assertRedirects(response, reverse('budget-list'))
        
        # Verify creation
        created = Budget.objects.get(category=self.category, month=9, year=2026)
        self.assertEqual(created.budget_amount, Decimal('150.00'))
        self.assertEqual(created.user, self.user)

    def test_budget_delete_view(self):
        self.client.force_login(self.user)
        # Renders confirm delete page
        response = self.client.get(reverse('budget-delete', args=[self.budget.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'budgets/budget_confirm_delete.html')
        
        # POST to delete
        response = self.client.post(reverse('budget-delete', args=[self.budget.pk]))
        self.assertRedirects(response, reverse('budget-list'))
        self.assertFalse(Budget.objects.filter(pk=self.budget.pk).exists())


class BudgetAlertHelpersTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alertuser', password='password123')
        self.category_food = Category.objects.create(user=self.user, name='Food')
        self.category_shop = Category.objects.create(user=self.user, name='Shopping')
        
        # Create user settings explicitly
        from accounts.models import UserSettings
        self.settings, _ = UserSettings.objects.get_or_create(user=self.user)
        self.settings.budget_threshold = 80
        self.settings.enable_budget_alerts = True
        self.settings.save()
        
        # Food Budget (5000)
        self.budget_food = Budget.objects.create(
            user=self.user,
            category=self.category_food,
            budget_amount=Decimal('5000.00'),
            month=6,
            year=2026
        )
        # Shopping Budget (3000)
        self.budget_shop = Budget.objects.create(
            user=self.user,
            category=self.category_shop,
            budget_amount=Decimal('3000.00'),
            month=6,
            year=2026
        )

    def test_alert_logic_warning_and_exceeded(self):
        from budgets.models import (
            get_budget_alerts,
            get_warning_budgets,
            get_exceeded_budgets,
            get_budget_alert_count
        )
        
        # Food Spent: 4200 (84% usage) -> Warning (since 84% >= 80% and < 100%)
        Expense.objects.create(
            user=self.user,
            name='Groceries',
            amount=Decimal('4200.00'),
            category=self.category_food,
            date=datetime.date(2026, 6, 10)
        )
        # Shopping Spent: 3500 (116.6% usage) -> Exceeded (since >= 100%)
        Expense.objects.create(
            user=self.user,
            name='Clothes',
            amount=Decimal('3500.00'),
            category=self.category_shop,
            date=datetime.date(2026, 6, 11)
        )
        
        # Check warnings
        warnings = get_warning_budgets(self.user, month=6, year=2026)
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0], self.budget_food)
        self.assertEqual(warnings[0].status_text, 'Warning')
        self.assertEqual(warnings[0].status_class, 'warning')
        
        # Check exceeded
        exceeded = get_exceeded_budgets(self.user, month=6, year=2026)
        self.assertEqual(len(exceeded), 1)
        self.assertEqual(exceeded[0], self.budget_shop)
        self.assertEqual(exceeded[0].status_text, 'Exceeded')
        self.assertEqual(exceeded[0].status_class, 'danger')
        
        # Check alerts list
        alerts = get_budget_alerts(self.user, month=6, year=2026)
        self.assertEqual(len(alerts), 2)
        
        # Check warning alert structure
        warning_alert = next(a for a in alerts if a['type'] == 'warning')
        self.assertEqual(warning_alert['budget'], self.budget_food)
        self.assertEqual(warning_alert['message'], "⚠ Food Budget has reached 84% of its allocated budget.")
        
        # Check exceeded alert structure
        exceeded_alert = next(a for a in alerts if a['type'] == 'exceeded')
        self.assertEqual(exceeded_alert['budget'], self.budget_shop)
        self.assertEqual(exceeded_alert['message'], "🚨 Shopping Budget exceeded by ₹500.")
        
        # Check count
        self.assertEqual(get_budget_alert_count(self.user, month=6, year=2026), 2)

    def test_alert_logic_disabled_settings(self):
        from budgets.models import (
            get_budget_alerts,
            get_warning_budgets,
            get_exceeded_budgets,
            get_budget_alert_count
        )
        
        # Disable alerts
        self.settings.enable_budget_alerts = False
        self.settings.save()
        
        # Food Spent: 4200 (84% usage) -> Normal (since enable_budget_alerts is False)
        Expense.objects.create(
            user=self.user,
            name='Groceries',
            amount=Decimal('4200.00'),
            category=self.category_food,
            date=datetime.date(2026, 6, 10)
        )
        # Shopping Spent: 3500 (116.6% usage) -> Exceeded
        Expense.objects.create(
            user=self.user,
            name='Clothes',
            amount=Decimal('3500.00'),
            category=self.category_shop,
            date=datetime.date(2026, 6, 11)
        )
        
        # Check warnings (should be empty because disabled)
        warnings = get_warning_budgets(self.user, month=6, year=2026)
        self.assertEqual(len(warnings), 0)
        self.assertEqual(self.budget_food.status_text, 'Normal')
        
        # Check exceeded (should be empty because disabled)
        exceeded = get_exceeded_budgets(self.user, month=6, year=2026)
        self.assertEqual(len(exceeded), 0)
        self.assertEqual(self.budget_shop.status_text, 'Exceeded')
        
        # Check alerts list (should be empty because disabled)
        alerts = get_budget_alerts(self.user, month=6, year=2026)
        self.assertEqual(len(alerts), 0)
