from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from decimal import Decimal
import datetime

from .models import Debt, Repayment

class DebtModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='debtuser', password='password123')

    def test_debt_properties_and_calculations(self):
        debt = Debt.objects.create(
            user=self.user,
            person_name='John Doe',
            debt_type='Borrowed',
            amount=Decimal('1000.00'),
            date=datetime.date(2026, 6, 1),
            due_date=datetime.date(2026, 6, 15)
        )
        
        self.assertEqual(debt.total_paid, Decimal('0.00'))
        self.assertEqual(debt.remaining_balance, Decimal('1000.00'))
        self.assertEqual(debt.status, 'Active')
        
        # Test payment creation updates status and balance
        pay1 = Repayment.objects.create(
            debt=debt,
            amount=Decimal('400.00'),
            date=datetime.date(2026, 6, 5)
        )
        self.assertEqual(debt.total_paid, Decimal('400.00'))
        self.assertEqual(debt.remaining_balance, Decimal('600.00'))
        self.assertEqual(debt.status, 'Active')

        # Test full repayment settles debt
        pay2 = Repayment.objects.create(
            debt=debt,
            amount=Decimal('600.00'),
            date=datetime.date(2026, 6, 10)
        )
        # Note: update_status is called inside save()
        debt.refresh_from_db()
        self.assertEqual(debt.total_paid, Decimal('1000.00'))
        self.assertEqual(debt.remaining_balance, Decimal('0.00'))
        self.assertEqual(debt.status, 'Settled')

        # Test payment deletion reverts status back to Active
        pay2.delete()
        debt.refresh_from_db()
        self.assertEqual(debt.total_paid, Decimal('400.00'))
        self.assertEqual(debt.remaining_balance, Decimal('600.00'))
        self.assertEqual(debt.status, 'Active')

    def test_overdue_property(self):
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        tomorrow = today + datetime.timedelta(days=1)

        # Overdue debt
        debt_overdue = Debt.objects.create(
            user=self.user,
            person_name='Jane Overdue',
            debt_type='Borrowed',
            amount=Decimal('500.00'),
            date=yesterday,
            due_date=yesterday
        )
        self.assertTrue(debt_overdue.is_overdue)

        # Non-overdue due tomorrow
        debt_future = Debt.objects.create(
            user=self.user,
            person_name='Joe Future',
            debt_type='Lent',
            amount=Decimal('500.00'),
            date=yesterday,
            due_date=tomorrow
        )
        self.assertFalse(debt_future.is_overdue)

        # Settled debt is never overdue
        debt_overdue.status = 'Settled'
        debt_overdue.save()
        self.assertFalse(debt_overdue.is_overdue)

    def test_amount_validations(self):
        # Negative amount validation
        debt = Debt(
            user=self.user,
            person_name='Error Person',
            debt_type='Borrowed',
            amount=Decimal('-10.00')
        )
        with self.assertRaises(ValidationError):
            debt.clean()


class DebtViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='viewuser', password='password123')
        self.other_user = User.objects.create_user(username='otheruser', password='password123')
        
        self.debt_borrowed = Debt.objects.create(
            user=self.user,
            person_name='Bob (Borrowed)',
            debt_type='Borrowed',
            amount=Decimal('500.00')
        )
        self.debt_lent = Debt.objects.create(
            user=self.user,
            person_name='Alice (Lent)',
            debt_type='Lent',
            amount=Decimal('1000.00')
        )
        self.other_debt = Debt.objects.create(
            user=self.other_user,
            person_name='Other Person',
            debt_type='Borrowed',
            amount=Decimal('200.00')
        )

    def test_list_view_and_aggregation(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('debt-list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Bob (Borrowed)')
        self.assertContains(response, 'Alice (Lent)')
        self.assertNotContains(response, 'Other Person')
        
        # Test aggregates context variables
        self.assertEqual(response.context['total_borrowed'], Decimal('500.00'))
        self.assertEqual(response.context['total_lent'], Decimal('1000.00'))
        self.assertEqual(response.context['total_to_pay'], Decimal('500.00'))
        self.assertEqual(response.context['total_to_receive'], Decimal('1000.00'))

    def test_list_filters(self):
        self.client.force_login(self.user)
        
        # Filter type
        response = self.client.get(reverse('debt-list') + '?debt_type=Borrowed')
        self.assertContains(response, 'Bob (Borrowed)')
        self.assertNotContains(response, 'Alice (Lent)')

        response = self.client.get(reverse('debt-list') + '?debt_type=Lent')
        self.assertNotContains(response, 'Bob (Borrowed)')
        self.assertContains(response, 'Alice (Lent)')

    def test_detail_view_and_payment_post(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('debt-detail', args=[self.debt_borrowed.pk]))
        self.assertEqual(response.status_code, 200)
        
        # Record payment via POST
        post_data = {
            'amount': '200.00',
            'date': '2026-06-10',
            'notes': 'First payment'
        }
        response = self.client.post(reverse('debt-detail', args=[self.debt_borrowed.pk]), data=post_data)
        self.assertRedirects(response, reverse('debt-detail', args=[self.debt_borrowed.pk]))
        
        # Verify payment created and parent updated
        self.debt_borrowed.refresh_from_db()
        self.assertEqual(self.debt_borrowed.total_paid, Decimal('200.00'))
        self.assertEqual(self.debt_borrowed.remaining_balance, Decimal('300.00'))
        
        # Over-payment verification (should fail validation)
        invalid_payment_data = {
            'amount': '400.00',  # exceeds 300.00 remaining
            'date': '2026-06-10',
        }
        response = self.client.post(reverse('debt-detail', args=[self.debt_borrowed.pk]), data=invalid_payment_data)
        # Should stay on page and render errors
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "cannot exceed the remaining balance")
