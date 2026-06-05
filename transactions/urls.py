from django.urls import path
from . import views

urlpatterns = [
    path('transactions/add/', views.AddTransactionView.as_view(), name='transaction-add'),
]
