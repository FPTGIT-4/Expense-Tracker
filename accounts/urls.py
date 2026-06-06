from django.urls import include, path
from .views import SignUpView, ProfileView, AccountListView, AccountCreateView, AccountUpdateView, AccountDeleteView

urlpatterns = [
    path('signup/', SignUpView.as_view(), name='signup'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('manage/', AccountListView.as_view(), name='account-list'),
    path('manage/add/', AccountCreateView.as_view(), name='account-add'),
    path('manage/<int:pk>/edit/', AccountUpdateView.as_view(), name='account-edit'),
    path('manage/<int:pk>/delete/', AccountDeleteView.as_view(), name='account-delete'),
    path('', include('django.contrib.auth.urls')),
]
