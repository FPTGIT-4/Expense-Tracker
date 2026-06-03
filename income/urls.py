from django.urls import path
from . import views

urlpatterns = [
    path('incomes/', views.IncomeListView.as_view(), name='income-list'),
    path('incomes/add/', views.IncomeCreateView.as_view(), name='income-add'),
    path('incomes/<int:pk>/edit/', views.IncomeUpdateView.as_view(), name='income-edit'),
    path('incomes/<int:pk>/delete/', views.IncomeDeleteView.as_view(), name='income-delete'),
]
