from django.urls import path
from . import views

urlpatterns = [
    path('incomes/', views.IncomeListView.as_view(), name='income-list'),
    path('incomes/add/', views.IncomeCreateView.as_view(), name='income-add'),
    path('incomes/<int:pk>/edit/', views.IncomeUpdateView.as_view(), name='income-edit'),
    path('incomes/<int:pk>/delete/', views.IncomeDeleteView.as_view(), name='income-delete'),

    path('expenses/', views.ExpenseListView.as_view(), name='expense-list'),
    path('expenses/add/', views.ExpenseCreateView.as_view(), name='expense-add'),
    path('expenses/<int:pk>/edit/', views.ExpenseUpdateView.as_view(), name='expense-edit'),
    path('expenses/<int:pk>/delete/', views.ExpenseDeleteView.as_view(), name='expense-delete'),
]
