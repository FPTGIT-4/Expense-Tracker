from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from decimal import Decimal
import datetime

from .models import Goal
from .forms import GoalForm, GoalQuickUpdateForm

class GoalModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='goalsuser', password='password123')

    def test_goal_calculations_and_properties(self):
        goal = Goal.objects.create(
            user=self.user,
            name='Emergency Fund',
            target_amount=Decimal('10000.00'),
            current_amount=Decimal('2500.00'),
            target_date=datetime.date(2026, 12, 31)
        )
        
        # Test calculations
        self.assertEqual(goal.progress_percentage, 25.0)
        self.assertEqual(goal.remaining_amount, Decimal('7500.00'))
        self.assertFalse(goal.is_completed)

        # Update and check completed state
        goal.current_amount = Decimal('10000.00')
        goal.save()
        self.assertEqual(goal.progress_percentage, 100.0)
        self.assertEqual(goal.remaining_amount, Decimal('0.00'))
        self.assertTrue(goal.is_completed)

        # Over-saved check
        goal.current_amount = Decimal('12000.00')
        goal.save()
        self.assertEqual(goal.progress_percentage, 100.0)
        self.assertEqual(goal.remaining_amount, Decimal('0.00'))
        self.assertTrue(goal.is_completed)

    def test_goal_validation_target_amount(self):
        # Target amount must be greater than zero
        goal = Goal(
            user=self.user,
            name='Trip to Tokyo',
            target_amount=Decimal('0.00'),
            current_amount=Decimal('0.00')
        )
        with self.assertRaises(ValidationError):
            goal.clean()

    def test_goal_validation_negative_current_amount(self):
        # Saved amount cannot be negative
        goal = Goal(
            user=self.user,
            name='House Downpayment',
            target_amount=Decimal('50000.00'),
            current_amount=Decimal('-100.00')
        )
        with self.assertRaises(ValidationError):
            goal.clean()


class GoalCRUDViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='viewsuser', password='password123')
        self.other_user = User.objects.create_user(username='otheruser', password='password123')
        
        self.goal = Goal.objects.create(
            user=self.user,
            name='New Laptop',
            target_amount=Decimal('2000.00'),
            current_amount=Decimal('500.00')
        )
        self.other_goal = Goal.objects.create(
            user=self.other_user,
            name='Other Goal',
            target_amount=Decimal('500.00'),
            current_amount=Decimal('100.00')
        )

    def test_goal_list_view_filtering(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('goal-list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'New Laptop')
        self.assertNotContains(response, 'Other Goal')

    def test_goal_search(self):
        self.client.force_login(self.user)
        # Match
        response = self.client.get(reverse('goal-list') + '?search=Lap')
        self.assertContains(response, 'New Laptop')
        # No match
        response = self.client.get(reverse('goal-list') + '?search=House')
        self.assertNotContains(response, 'New Laptop')

    def test_goal_status_filter(self):
        self.client.force_login(self.user)
        
        # Add a completed goal
        completed_goal = Goal.objects.create(
            user=self.user,
            name='Vacation',
            target_amount=Decimal('1000.00'),
            current_amount=Decimal('1000.00')
        )

        # Filter active
        response = self.client.get(reverse('goal-list') + '?status=active')
        self.assertContains(response, 'New Laptop')
        self.assertNotContains(response, 'Vacation')

        # Filter completed
        response = self.client.get(reverse('goal-list') + '?status=completed')
        self.assertNotContains(response, 'New Laptop')
        self.assertContains(response, 'Vacation')

    def test_goal_detail_view_and_quick_update(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('goal-detail', args=[self.goal.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'New Laptop')

        # Quick update amount post
        response = self.client.post(reverse('goal-detail', args=[self.goal.pk]), data={
            'current_amount': '1500.00'
        })
        self.assertRedirects(response, reverse('goal-detail', args=[self.goal.pk]))
        
        # Verify update
        self.goal.refresh_from_db()
        self.assertEqual(self.goal.current_amount, Decimal('1500.00'))

    def test_goal_create_view(self):
        self.client.force_login(self.user)
        form_data = {
            'name': 'Wedding Savings',
            'target_amount': '10000.00',
            'current_amount': '500.00',
            'target_date': '2026-10-15',
            'description': 'Main wedding event fund'
        }
        response = self.client.post(reverse('goal-add'), data=form_data)
        self.assertRedirects(response, reverse('goal-list'))
        
        created = Goal.objects.get(name='Wedding Savings', user=self.user)
        self.assertEqual(created.target_amount, Decimal('10000.00'))

    def test_goal_delete_view(self):
        self.client.force_login(self.user)
        # Get confirm
        response = self.client.get(reverse('goal-delete', args=[self.goal.pk]))
        self.assertEqual(response.status_code, 200)
        
        # Post delete
        response = self.client.post(reverse('goal-delete', args=[self.goal.pk]))
        self.assertRedirects(response, reverse('goal-list'))
        self.assertFalse(Goal.objects.filter(pk=self.goal.pk).exists())
