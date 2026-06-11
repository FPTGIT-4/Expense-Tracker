from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from decimal import Decimal
import datetime

from .models import RecurringTransaction, GeneratedOccurrence
from categories.models import Category
from accounts.models import Account
from income.models import Income
from expenses.models import Expense
from companies.models import CompanyAccount, CompanyIncome, CompanyExpense
from .utils import generate_recurring_transactions, get_expected_occurrences

class RecurrenceModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='recuruser', password='password123')
        self.category = Category.objects.create(user=self.user, name='Utilities')

    def test_monthly_equivalent_calculations(self):
        # Daily
        daily = RecurringTransaction(user=self.user, name='Daily Sub', transaction_type='Expense', amount=Decimal('1.00'), category=self.category, frequency='Daily', start_date=datetime.date(2026, 6, 1))
        self.assertEqual(daily.monthly_equivalent, Decimal('30.00'))
        
        # Weekly
        weekly = RecurringTransaction(user=self.user, name='Weekly Meal', transaction_type='Expense', amount=Decimal('10.00'), category=self.category, frequency='Weekly', start_date=datetime.date(2026, 6, 1))
        self.assertEqual(weekly.monthly_equivalent, Decimal('43.30'))

        # Monthly
        monthly = RecurringTransaction(user=self.user, name='Rent', transaction_type='Expense', amount=Decimal('1200.00'), category=self.category, frequency='Monthly', start_date=datetime.date(2026, 6, 1))
        self.assertEqual(monthly.monthly_equivalent, Decimal('1200.00'))

        # Quarterly
        quarterly = RecurringTransaction(user=self.user, name='Tax', transaction_type='Expense', amount=Decimal('300.00'), category=self.category, frequency='Quarterly', start_date=datetime.date(2026, 6, 1))
        self.assertEqual(quarterly.monthly_equivalent, Decimal('100.00'))

        # Yearly
        yearly = RecurringTransaction(user=self.user, name='Insurance', transaction_type='Expense', amount=Decimal('120.00'), category=self.category, frequency='Yearly', start_date=datetime.date(2026, 6, 1))
        self.assertEqual(yearly.monthly_equivalent, Decimal('10.00'))

    def test_expected_occurrences_calculation(self):
        recur = RecurringTransaction.objects.create(
            user=self.user,
            name='Daily Sub',
            transaction_type='Expense',
            amount=Decimal('5.00'),
            category=self.category,
            frequency='Daily',
            start_date=datetime.date(2026, 6, 1),
            end_date=datetime.date(2026, 6, 5)
        )
        
        dates = get_expected_occurrences(recur, today=datetime.date(2026, 6, 10))
        self.assertEqual(len(dates), 5)
        self.assertEqual(dates[0], datetime.date(2026, 6, 1))
        self.assertEqual(dates[-1], datetime.date(2026, 6, 5))


class RecurrenceGeneratorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='genuser', password='password123')
        self.category = Category.objects.create(user=self.user, name='Salary')
        self.account = Account.objects.create(user=self.user, name='Cash', account_type='Cash', initial_balance=Decimal('0.00'))
        
        self.company_account = CompanyAccount.objects.create(
            user=self.user,
            name='Acme Corp',
            opening_balance=Decimal('1000.00')
        )

    def test_personal_income_generation(self):
        # Create active weekly income starting 2 weeks ago
        start_date = datetime.date.today() - datetime.timedelta(days=14)
        recur = RecurringTransaction.objects.create(
            user=self.user,
            name='Weekly Freelance',
            transaction_type='Income',
            amount=Decimal('200.00'),
            category=self.category,
            account=self.account,
            frequency='Weekly',
            start_date=start_date
        )

        # Generate occurrences
        generate_recurring_transactions(self.user)

        # Expected occurrences: start_date (T-14), start_date + 7 (T-7), start_date + 14 (T-0) -> 3 entries
        self.assertEqual(Income.objects.filter(user=self.user).count(), 3)
        self.assertEqual(GeneratedOccurrence.objects.filter(recurring_transaction=recur).count(), 3)

        # Re-running generation does not duplicate records
        generate_recurring_transactions(self.user)
        self.assertEqual(Income.objects.filter(user=self.user).count(), 3)

    def test_company_expense_generation(self):
        start_date = datetime.date.today() - datetime.timedelta(days=2)
        recur = RecurringTransaction.objects.create(
            user=self.user,
            name='Co-Working Rent',
            transaction_type='Expense',
            amount=Decimal('150.00'),
            category=self.category,
            company_account=self.company_account,
            frequency='Daily',
            start_date=start_date
        )

        generate_recurring_transactions(self.user)
        
        # Expected occurrences: start_date (T-2), T-1, T-0 -> 3 entries
        self.assertEqual(CompanyExpense.objects.filter(company_account=self.company_account).count(), 3)
        self.assertEqual(GeneratedOccurrence.objects.filter(recurring_transaction=recur).count(), 3)


class RecurrenceViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='viewuser', password='password123')
        self.category = Category.objects.create(user=self.user, name='Subscription')
        self.client.force_login(self.user)

    def test_create_and_toggle_views(self):
        # Create configuration
        response = self.client.post(reverse('recurring-add'), data={
            'name': 'Netflix',
            'transaction_type': 'Expense',
            'amount': '15.99',
            'category': self.category.pk,
            'frequency': 'Monthly',
            'start_date': '2026-06-01',
            'status': 'Active'
        })
        self.assertRedirects(response, reverse('recurring-list'))
        
        recur = RecurringTransaction.objects.get(name='Netflix', user=self.user)
        self.assertEqual(recur.status, 'Active')

        # Toggle configuration (pauses it)
        response = self.client.get(reverse('recurring-toggle', args=[recur.pk]))
        self.assertRedirects(response, reverse('recurring-detail', args=[recur.pk]))
        
        recur.refresh_from_db()
        self.assertEqual(recur.status, 'Inactive')
