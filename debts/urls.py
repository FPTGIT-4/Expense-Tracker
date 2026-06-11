from django.urls import path
from . import views

urlpatterns = [
    path('', views.DebtListView.as_view(), name='debt-list'),
    path('add/', views.DebtCreateView.as_view(), name='debt-add'),
    path('<int:pk>/', views.DebtDetailView.as_view(), name='debt-detail'),
    path('<int:pk>/edit/', views.DebtUpdateView.as_view(), name='debt-edit'),
    path('<int:pk>/delete/', views.DebtDeleteView.as_view(), name='debt-delete'),
    path('payment/<int:pk>/delete/', views.RepaymentDeleteView.as_view(), name='repayment-delete'),
]
