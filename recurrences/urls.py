from django.urls import path
from . import views

urlpatterns = [
    path('', views.RecurringTransactionListView.as_view(), name='recurring-list'),
    path('add/', views.RecurringTransactionCreateView.as_view(), name='recurring-add'),
    path('<int:pk>/', views.RecurringTransactionDetailView.as_view(), name='recurring-detail'),
    path('<int:pk>/edit/', views.RecurringTransactionUpdateView.as_view(), name='recurring-edit'),
    path('<int:pk>/delete/', views.RecurringTransactionDeleteView.as_view(), name='recurring-delete'),
    path('<int:pk>/toggle/', views.RecurringTransactionToggleView.as_view(), name='recurring-toggle'),
]
