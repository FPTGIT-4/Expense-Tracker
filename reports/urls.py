from django.urls import path
from .views import ReportsDashboardView, AccountReportsView

urlpatterns = [
    path('reports/', ReportsDashboardView.as_view(), name='reports-dashboard'),
    path('reports/accounts/', AccountReportsView.as_view(), name='account-reports'),
]
