from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.db import transaction, IntegrityError
from .models import Category

class CategoryModelTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='password123')
        self.user2 = User.objects.create_user(username='user2', password='password123')

    def test_category_creation(self):
        category = Category.objects.create(
            user=self.user1,
            name='Food',
            description='Eating out'
        )
        self.assertEqual(category.name, 'Food')
        self.assertEqual(category.description, 'Eating out')
        self.assertEqual(category.user, self.user1)
        self.assertEqual(str(category), 'Food')

    def test_category_unique_together_constraint(self):
        Category.objects.create(user=self.user1, name='Food')
        # Same user, same name should raise IntegrityError
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Category.objects.create(user=self.user1, name='Food')
        
        # Different user, same name should be allowed
        category_other_user = Category.objects.create(user=self.user2, name='Food')
        self.assertEqual(category_other_user.name, 'Food')

class CategoryViewsTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', password='password123')
        self.user2 = User.objects.create_user(username='user2', password='password123')
        self.cat1 = Category.objects.create(user=self.user1, name='Food', description='User 1 Food')
        self.cat2 = Category.objects.create(user=self.user2, name='Entertainment', description='User 2 Entertainment')

    def test_category_list_login_required(self):
        response = self.client.get(reverse('category-list'))
        self.assertNotEqual(response.status_code, 200) # Should redirect to login

    def test_category_list_user_isolation(self):
        self.client.force_login(self.user1)
        response = self.client.get(reverse('category-list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Food')
        self.assertNotContains(response, 'Entertainment')

    def test_category_create_post(self):
        self.client.force_login(self.user1)
        response = self.client.post(reverse('category-add'), {
            'name': 'Utilities',
            'description': 'Electricity and Water'
        })
        self.assertEqual(response.status_code, 302) # Redirect to list
        self.assertTrue(Category.objects.filter(user=self.user1, name='Utilities').exists())

    def test_category_update_owner(self):
        self.client.force_login(self.user1)
        response = self.client.post(reverse('category-edit', kwargs={'pk': self.cat1.pk}), {
            'name': 'Dining Out',
            'description': 'Updated desc'
        })
        self.assertEqual(response.status_code, 302)
        self.cat1.refresh_from_db()
        self.assertEqual(self.cat1.name, 'Dining Out')

    def test_category_update_non_owner(self):
        self.client.force_login(self.user2)
        response = self.client.post(reverse('category-edit', kwargs={'pk': self.cat1.pk}), {
            'name': 'Hacked',
            'description': 'Hacked'
        })
        self.assertEqual(response.status_code, 404) # Should return 404 since it's filtered out

    def test_category_delete_owner(self):
        self.client.force_login(self.user1)
        response = self.client.post(reverse('category-delete', kwargs={'pk': self.cat1.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Category.objects.filter(pk=self.cat1.pk).exists())

    def test_category_delete_non_owner(self):
        self.client.force_login(self.user2)
        response = self.client.post(reverse('category-delete', kwargs={'pk': self.cat1.pk}))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Category.objects.filter(pk=self.cat1.pk).exists())
