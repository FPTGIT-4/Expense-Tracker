from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal
import datetime

from accounts.models import Account, AccountTransfer, UserSettings
from categories.models import Category
from income.models import Income
from expenses.models import Expense
from budgets.models import Budget

class ExpenseTrackerAPITests(APITestCase):

    def setUp(self):
        # Create users
        self.user1 = User.objects.create_user(username='testuser1', password='password123', email='test1@example.com')
        self.user2 = User.objects.create_user(username='testuser2', password='password123', email='test2@example.com')
        
        # Default settings and cash account are created on registration API, but since we created using model manager,
        # let's set them up manually for setup.
        self.settings1, _ = UserSettings.objects.get_or_create(user=self.user1)
        self.account1, _ = Account.objects.get_or_create(
            user=self.user1, name='Main Account', account_type='Bank Account',
            defaults={'initial_balance': Decimal('1000.00')}
        )

        # Login url
        self.login_url = reverse('api-login')
        self.register_url = reverse('api-register')
        self.dashboard_url = reverse('api-dashboard')
        self.settings_url = reverse('api-settings')
        self.notifications_url = reverse('api-notifications')
        self.reports_url = reverse('api-reports')

    def test_user_registration_creates_defaults(self):
        """Test registration endpoint creates defaults settings and Cash account."""
        response = self.client.post(self.register_url, {
            'username': 'newuser',
            'password': 'newpassword123',
            'confirm_password': 'newpassword123',
            'email': 'new@example.com',
            'first_name': 'New',
            'last_name': 'User'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        
        user = User.objects.get(username='newuser')
        # Check settings
        self.assertTrue(UserSettings.objects.filter(user=user).exists())
        # Check Cash account
        self.assertTrue(Account.objects.filter(user=user, name='Cash').exists())

    def test_token_authentication_flow(self):
        """Test login, accessing protected resource, and logout."""
        # 1. Login
        response = self.client.post(self.login_url, {
            'username': 'testuser1',
            'password': 'password123'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        token = response.data['token']
        self.assertIsNotNone(token)

        # 2. Access protected endpoint without token
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # 3. Access protected endpoint with token
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token)
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 4. Logout
        logout_url = reverse('api-logout')
        response = self.client.post(logout_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 5. Access again after logout
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_account_crud_operations(self):
        """Test standard CRUD operations on Account endpoints."""
        response = self.client.post(self.login_url, {'username': 'testuser1', 'password': 'password123'})
        token = response.data['token']
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token)

        accounts_url = reverse('api-accounts-list')

        # Create
        response = self.client.post(accounts_url, {
            'name': 'Savings Wallet',
            'account_type': 'Wallet',
            'initial_balance': '500.00',
            'minimum_balance': '50.00',
            'status': 'ACTIVE'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        account_id = response.data['id']

        # Read (List)
        response = self.client.get(accounts_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Main Account and Savings Wallet
        self.assertEqual(response.data['count'], 2) 

        # Read (Detail)
        detail_url = reverse('api-accounts-detail', args=[account_id])
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Savings Wallet')

        # Update (Patch)
        response = self.client.patch(detail_url, {'notes': 'Test notes here'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['notes'], 'Test notes here')

        # Delete
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_categories_crud(self):
        """Test Category CRUD API endpoints."""
        response = self.client.post(self.login_url, {'username': 'testuser1', 'password': 'password123'})
        token = response.data['token']
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token)

        categories_url = reverse('api-categories-list')

        # Create category
        response = self.client.post(categories_url, {'name': 'Groceries', 'description': 'Monthly grocery bills'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        category_id = response.data['id']

        # List category
        response = self.client.get(categories_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_incomes_and_expenses_crud(self):
        """Test CRUD on Income and Expense models with account integration."""
        response = self.client.post(self.login_url, {'username': 'testuser1', 'password': 'password123'})
        token = response.data['token']
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token)

        # Setup: create Category
        cat = Category.objects.create(user=self.user1, name='Entertainment')

        # Create Income
        income_url = reverse('api-income-list')
        response = self.client.post(income_url, {
            'account': self.account1.id,
            'amount': '350.00',
            'source': 'Freelancing',
            'date': '2026-06-09',
            'description': 'Gig economy task'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Create Expense
        expense_url = reverse('api-expenses-list')
        response = self.client.post(expense_url, {
            'account': self.account1.id,
            'category': cat.id,
            'name': 'Movie Tickets',
            'amount': '120.00',
            'date': '2026-06-09'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check Account balance updates automatically (1000 initial + 350 income - 120 expense = 1230.00)
        self.account1.refresh_from_db()
        self.assertEqual(self.account1.current_balance, Decimal('1230.00'))

    def test_transfer_funds_validation(self):
        """Test transfer endpoint verifies accounts ownership, balances, and types."""
        response = self.client.post(self.login_url, {'username': 'testuser1', 'password': 'password123'})
        token = response.data['token']
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token)

        # Setup destination account
        dest_account = Account.objects.create(user=self.user1, name='Cash Wallet', account_type='Wallet', initial_balance=Decimal('100.00'))

        transfers_url = reverse('api-transfers-list')
        response = self.client.post(transfers_url, {
            'from_account': self.account1.id,
            'to_account': dest_account.id,
            'amount': '250.00',
            'transfer_date': '2026-06-09',
            'note': 'API money transfer test'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify updated balances
        self.account1.refresh_from_db()
        dest_account.refresh_from_db()
        self.assertEqual(self.account1.current_balance, Decimal('750.00'))
        self.assertEqual(dest_account.current_balance, Decimal('350.00'))

    def test_budget_creation_and_progress(self):
        """Test Budget endpoints, status flags, alerts warning count."""
        response = self.client.post(self.login_url, {'username': 'testuser1', 'password': 'password123'})
        token = response.data['token']
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token)

        cat = Category.objects.create(user=self.user1, name='Dining Out')
        
        # Create Budget
        budgets_url = reverse('api-budgets-list')
        response = self.client.post(budgets_url, {
            'category': cat.id,
            'budget_amount': '500.00',
            'month': 6,
            'year': 2026,
            'is_active': True
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status_text'], 'Normal')

        # Add an expense under this category to trigger alert thresholds
        Expense.objects.create(
            user=self.user1, account=self.account1, category=cat,
            name='Luxury dinner', amount=Decimal('420.00'), date=datetime.date(2026, 6, 9)
        )

        # Fetch detail and verify usage
        detail_url = reverse('api-budgets-detail', args=[response.data['id']])
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_spent'], '420.00')
        # 420 / 500 = 84% > 80% default threshold
        self.assertEqual(response.data['status_text'], 'Warning') 

    def test_dashboard_and_reports_output(self):
        """Test dashboard, notifications, and reports endpoints return structured JSON."""
        response = self.client.post(self.login_url, {'username': 'testuser1', 'password': 'password123'})
        token = response.data['token']
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token)

        # 1. Dashboard API
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_balance', response.data)
        self.assertIn('monthly_income', response.data)
        self.assertIn('recent_activity', response.data)

        # 2. Notifications API
        response = self.client.get(self.notifications_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('budget_alerts', response.data)
        self.assertIn('low_balance_alerts', response.data)

        # 3. Reports API
        response = self.client.get(self.reports_url, {'date_filter': 'this_month'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('category_expense_distribution', response.data)
        self.assertIn('recent_transactions', response.data)
