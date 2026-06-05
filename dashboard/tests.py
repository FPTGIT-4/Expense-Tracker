from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from decimal import Decimal
import datetime
from categories.models import Category
from income.models import Income
from expenses.models import Expense

class DashboardViewTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='password123')
        self.user2 = User.objects.create_user(username='user2', password='password123')
        
        # Setup for user1
        self.cat1 = Category.objects.create(user=self.user1, name='Food')
        self.cat2 = Category.objects.create(user=self.user1, name='Utilities')
        
        self.income1 = Income.objects.create(
            user=self.user1,
            amount=Decimal('5000.00'),
            source='Salary',
            date=datetime.date.today(),
            description='Monthly salary'
        )
        self.expense1 = Expense.objects.create(
            user=self.user1,
            name='Groceries',
            amount=Decimal('150.00'),
            date=datetime.date.today(),
            category=self.cat1,
            description='Weekly Groceries'
        )
        
        # Setup for user2
        self.cat3 = Category.objects.create(user=self.user2, name='Rent')
        self.income2 = Income.objects.create(
            user=self.user2,
            amount=Decimal('3000.00'),
            source='Freelancing',
            date=datetime.date.today() - datetime.timedelta(days=1),
            description='Side job'
        )

    def test_dashboard_login_required(self):
        response = self.client.get(reverse('dashboard'))
        self.assertNotEqual(response.status_code, 200)
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('dashboard')}")

    def test_dashboard_statistics_calculation_user1(self):
        self.client.force_login(self.user1)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        
        # Verify Context stats
        self.assertEqual(response.context['total_income'], Decimal('5000.00'))
        self.assertEqual(response.context['total_expenses'], Decimal('150.00'))
        self.assertEqual(response.context['current_balance'], Decimal('4850.00'))
        self.assertEqual(response.context['total_categories'], 2)
        
        # Verify Today's statistics
        self.assertEqual(response.context['income_today'], Decimal('5000.00'))
        self.assertEqual(response.context['expenses_today'], Decimal('150.00'))

    def test_dashboard_statistics_calculation_user2(self):
        self.client.force_login(self.user2)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        
        # Verify Context stats for user2 (income was yesterday, so today's stats should be 0)
        self.assertEqual(response.context['total_income'], Decimal('3000.00'))
        self.assertEqual(response.context['total_expenses'], Decimal('0.00'))
        self.assertEqual(response.context['current_balance'], Decimal('3000.00'))
        self.assertEqual(response.context['total_categories'], 1)
        self.assertEqual(response.context['income_today'], Decimal('0.00'))
        self.assertEqual(response.context['expenses_today'], Decimal('0.00'))

    def test_quick_add_income(self):
        self.client.force_login(self.user1)
        # Verify initial count
        initial_count = Income.objects.filter(user=self.user1).count()
        
        response = self.client.post(reverse('dashboard'), {
            'action': 'add_income',
            'amount': '350.00',
            'source': 'Freelancing',
            'description': 'Quick consulting session'
        })
        # Check redirect on success
        self.assertRedirects(response, reverse('dashboard'))
        
        # Verify database record creation
        self.assertEqual(Income.objects.filter(user=self.user1).count(), initial_count + 1)
        new_income = Income.objects.filter(user=self.user1).order_by('-created_at').first()
        self.assertEqual(new_income.amount, Decimal('350.00'))
        self.assertEqual(new_income.source, 'Freelancing')
        self.assertEqual(new_income.date, datetime.date.today())

    def test_quick_add_expense(self):
        self.client.force_login(self.user1)
        # Verify initial count
        initial_count = Expense.objects.filter(user=self.user1).count()
        
        response = self.client.post(reverse('dashboard'), {
            'action': 'add_expense',
            'name': 'Internet bill',
            'amount': '60.00',
            'category': self.cat2.id,
            'description': 'Monthly subscription'
        })
        # Check redirect on success
        self.assertRedirects(response, reverse('dashboard'))
        
        # Verify database record creation
        self.assertEqual(Expense.objects.filter(user=self.user1).count(), initial_count + 1)
        new_expense = Expense.objects.filter(user=self.user1).order_by('-created_at').first()
        self.assertEqual(new_expense.name, 'Internet bill')
        self.assertEqual(new_expense.amount, Decimal('60.00'))
        self.assertEqual(new_expense.category, self.cat2)
        self.assertEqual(new_expense.date, datetime.date.today())
