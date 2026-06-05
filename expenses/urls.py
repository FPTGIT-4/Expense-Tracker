from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    path('expenses/', views.ExpenseListView.as_view(), name='expense-list'),
    # Redirect old "Add Expense" URL to the Unified Add Transaction page (Expense tab)
    path('expenses/add/', RedirectView.as_view(url='/transactions/add/?tab=expense', permanent=False), name='expense-add'),
    path('expenses/<int:pk>/edit/', views.ExpenseUpdateView.as_view(), name='expense-edit'),
    path('expenses/<int:pk>/delete/', views.ExpenseDeleteView.as_view(), name='expense-delete'),
]
