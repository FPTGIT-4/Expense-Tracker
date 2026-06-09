from django.urls import include, path
from .views import (
    SignUpView, ProfileView, SettingsView, AccountListView, AccountCreateView, 
    AccountUpdateView, AccountDeleteView, AccountDetailView, 
    AccountTransferCreateView, TransferListView, TransferDetailView,
    ThemeToggleView,
)

urlpatterns = [
    path('signup/', SignUpView.as_view(), name='signup'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('settings/', SettingsView.as_view(), name='settings'),
    path('theme-toggle/', ThemeToggleView.as_view(), name='theme-toggle'),
    path('manage/', AccountListView.as_view(), name='account-list'),
    path('manage/add/', AccountCreateView.as_view(), name='account-add'),
    path('manage/transfer/', AccountTransferCreateView.as_view(), name='account-transfer'),
    path('manage/transfers/', TransferListView.as_view(), name='transfer-list'),
    path('manage/transfers/<int:pk>/', TransferDetailView.as_view(), name='transfer-detail'),
    path('manage/<int:pk>/edit/', AccountUpdateView.as_view(), name='account-edit'),
    path('manage/<int:pk>/delete/', AccountDeleteView.as_view(), name='account-delete'),
    path('<int:pk>/', AccountDetailView.as_view(), name='account-detail'),
    path('', include('django.contrib.auth.urls')),
]
