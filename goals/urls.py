from django.urls import path
from . import views

urlpatterns = [
    path('', views.GoalListView.as_view(), name='goal-list'),
    path('add/', views.GoalCreateView.as_view(), name='goal-add'),
    path('<int:pk>/', views.GoalDetailView.as_view(), name='goal-detail'),
    path('<int:pk>/edit/', views.GoalUpdateView.as_view(), name='goal-edit'),
    path('<int:pk>/delete/', views.GoalDeleteView.as_view(), name='goal-delete'),
]
