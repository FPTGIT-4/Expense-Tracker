from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from decimal import Decimal
import datetime
from categories.models import Category
from income.models import Income
from expenses.models import Expense
from .services import ReportDataService

class ReportsViewTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='password123')
        self.user2 = User.objects.create_user(username='user2', password='password123')

        self.cat1 = Category.objects.create(user=self.user1, name='Food')
        self.cat2 = Category.objects.create(user=self.user1, name='Bills')

        # User 1 Transactions
        self.income1 = Income.objects.create(
            user=self.user1,
            amount=Decimal('1000.00'),
            source='Salary',
            date=datetime.date.today()
        )
        self.income2 = Income.objects.create(
            user=self.user1,
            amount=Decimal('500.00'),
            source='Freelancing',
            date=datetime.date.today() - datetime.timedelta(days=2)
        )
        self.expense1 = Expense.objects.create(
            user=self.user1,
            name='Lunch',
            amount=Decimal('50.00'),
            date=datetime.date.today(),
            category=self.cat1
        )
        self.expense2 = Expense.objects.create(
            user=self.user1,
            name='Electric bill',
            amount=Decimal('150.00'),
            date=datetime.date.today() - datetime.timedelta(days=2),
            category=self.cat2
        )

        # User 2 Transaction
        self.income3 = Income.objects.create(
            user=self.user2,
            amount=Decimal('3000.00'),
            source='Business',
            date=datetime.date.today()
        )

    def test_reports_login_required(self):
        response = self.client.get(reverse('reports-dashboard'))
        self.assertNotEqual(response.status_code, 200)

    def test_reports_default_filter_this_month(self):
        self.client.force_login(self.user1)
        response = self.client.get(reverse('reports-dashboard'))
        self.assertEqual(response.status_code, 200)
        
        data = ReportDataService.get_report_data(
            self.user1, 
            datetime.date.today().replace(day=1), 
            datetime.date.today()
        )
        self.assertEqual(data['total_income'], Decimal('1500.00'))
        self.assertEqual(data['total_expenses'], Decimal('200.00'))
        self.assertEqual(data['net_balance'], Decimal('1300.00'))

    def test_reports_today_filter(self):
        self.client.force_login(self.user1)
        response = self.client.get(reverse('reports-dashboard'), {'date_filter': 'today'})
        self.assertEqual(response.status_code, 200)
        
        self.assertEqual(response.context['total_income'], Decimal('1000.00'))
        self.assertEqual(response.context['total_expenses'], Decimal('50.00'))
        self.assertEqual(response.context['net_balance'], Decimal('950.00'))

    def test_reports_user_isolation(self):
        self.client.force_login(self.user2)
        response = self.client.get(reverse('reports-dashboard'), {'date_filter': 'today'})
        self.assertEqual(response.status_code, 200)
        # User 2 only has one income of $3000.00
        self.assertEqual(response.context['total_income'], Decimal('3000.00'))
        self.assertEqual(response.context['total_expenses'], Decimal('0.00'))
        self.assertEqual(response.context['net_balance'], Decimal('3000.00'))
