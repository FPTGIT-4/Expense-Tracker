from django.urls import path
from . import views

urlpatterns = [
    path('categories/', views.CategoryListView.as_view(), name='category-list'),
    path('categories/add/', views.CategoryCreateView.as_view(), name='category-add'),
    path('categories/<int:pk>/edit/', views.CategoryUpdateView.as_view(), name='category-edit'),
    path('categories/<int:pk>/delete/', views.CategoryDeleteView.as_view(), name='category-delete'),

    # Labels CRUD URL patterns
    path('labels/add/', views.LabelCreateView.as_view(), name='label-add'),
    path('labels/<int:pk>/edit/', views.LabelUpdateView.as_view(), name='label-edit'),
    path('labels/<int:pk>/delete/', views.LabelDeleteView.as_view(), name='label-delete'),
]
