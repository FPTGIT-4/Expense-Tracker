from django.urls import path
from .views import ExpensePlaceholderView

urlpatterns = [
    path('expenses/', ExpensePlaceholderView.as_view(), name='expense-list'),
]
