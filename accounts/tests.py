from django.test import TestCase
from django.urls import reverse, resolve
from django.contrib.auth.models import User

class ProfileViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='profiletest', 
            password='password123',
            email='test@example.com',
            first_name='John',
            last_name='Doe'
        )

    def test_profile_redirects_for_anonymous_user(self):
        response = self.client.get(reverse('profile'))
        self.assertNotEqual(response.status_code, 200)
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('profile')}")

    def test_profile_renders_logged_in_user_data(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/profile.html')
        
        # Verify details in output
        self.assertContains(response, 'profiletest')
        self.assertContains(response, 'John Doe')
        self.assertContains(response, 'test@example.com')
        self.assertContains(response, 'Date Joined')

    def test_password_change_url_resolves(self):
        url = reverse('password_change')
        self.assertEqual(resolve(url).view_name, 'password_change')
