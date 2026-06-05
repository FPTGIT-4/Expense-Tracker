from django.urls import path
from .views import ReportsDashboardView

urlpatterns = [
    path('reports/', ReportsDashboardView.as_view(), name='reports-dashboard'),
]
