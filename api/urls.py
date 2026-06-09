from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    LoginAPIView, LogoutAPIView, RegisterAPIView, UserSettingsAPIView,
    AccountViewSet, AccountTransferViewSet, CategoryViewSet,
    IncomeViewSet, ExpenseViewSet, BudgetViewSet,
    DashboardSummaryAPIView, NotificationAPIView, ReportAPIView
)

router = DefaultRouter()
router.register('accounts', AccountViewSet, basename='api-accounts')
router.register('transfers', AccountTransferViewSet, basename='api-transfers')
router.register('categories', CategoryViewSet, basename='api-categories')
router.register('income', IncomeViewSet, basename='api-income')
router.register('expenses', ExpenseViewSet, basename='api-expenses')
router.register('budgets', BudgetViewSet, basename='api-budgets')

urlpatterns = [
    # Router endpoints
    path('', include(router.urls)),

    # Authentication
    path('auth/login/', LoginAPIView.as_view(), name='api-login'),
    path('auth/logout/', LogoutAPIView.as_view(), name='api-logout'),
    path('auth/register/', RegisterAPIView.as_view(), name='api-register'),

    # User Settings
    path('settings/', UserSettingsAPIView.as_view(), name='api-settings'),

    # Dashboards and Analytics
    path('dashboard/', DashboardSummaryAPIView.as_view(), name='api-dashboard'),
    path('notifications/', NotificationAPIView.as_view(), name='api-notifications'),
    path('reports/', ReportAPIView.as_view(), name='api-reports'),
]
