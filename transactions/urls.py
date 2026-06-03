from django.urls import path
from . import views

urlpatterns = [
    path('', views.IncomeListView.as_view(), name='income-list'),
    path('add/', views.IncomeCreateView.as_view(), name='income-add'),
    path('<int:pk>/edit/', views.IncomeUpdateView.as_view(), name='income-edit'),
    path('<int:pk>/delete/', views.IncomeDeleteView.as_view(), name='income-delete'),
]
