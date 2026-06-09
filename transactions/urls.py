from django.urls import path
from . import views

urlpatterns = [
    path('transactions/add/', views.AddTransactionView.as_view(), name='transaction-add'),
    path('transactions/history/', views.TransactionHistoryListView.as_view(), name='transaction-history'),
    path('transactions/history/<int:pk>/', views.TransactionHistoryDetailView.as_view(), name='transaction-history-detail'),
]
