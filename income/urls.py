from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    path('incomes/', views.IncomeListView.as_view(), name='income-list'),
    # Redirect old "Add Income" URL to the Unified Add Transaction page (Income tab)
    path('incomes/add/', RedirectView.as_view(url='/transactions/add/?tab=income', permanent=False), name='income-add'),
    path('incomes/create/', views.IncomeCreateView.as_view(), name='income-create'),
    path('incomes/<int:pk>/edit/', views.IncomeUpdateView.as_view(), name='income-edit'),
    path('incomes/<int:pk>/delete/', views.IncomeDeleteView.as_view(), name='income-delete'),
]
