from django.urls import path
from . import views

urlpatterns = [
    path('', views.CompanyAccountListView.as_view(), name='company-account-list'),
    path('add/', views.CompanyAccountCreateView.as_view(), name='company-account-add'),
    path('<int:pk>/', views.CompanyAccountDetailView.as_view(), name='company-account-detail'),
    path('<int:pk>/edit/', views.CompanyAccountUpdateView.as_view(), name='company-account-edit'),
    path('<int:pk>/delete/', views.CompanyAccountDeleteView.as_view(), name='company-account-delete'),
    
    path('dashboard/', views.CompanyDashboardView.as_view(), name='company-dashboard'),
    path('reports/', views.CompanyReportsView.as_view(), name='company-reports'),

    # Income CRUD
    path('income/add/', views.CompanyIncomeCreateView.as_view(), name='company-income-add'),
    path('income/<int:pk>/edit/', views.CompanyIncomeUpdateView.as_view(), name='company-income-edit'),
    path('income/<int:pk>/delete/', views.CompanyIncomeDeleteView.as_view(), name='company-income-delete'),

    # Expense CRUD
    path('expense/add/', views.CompanyExpenseCreateView.as_view(), name='company-expense-add'),
    path('expense/<int:pk>/edit/', views.CompanyExpenseUpdateView.as_view(), name='company-expense-edit'),
    path('expense/<int:pk>/delete/', views.CompanyExpenseDeleteView.as_view(), name='company-expense-delete'),
]
