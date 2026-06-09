from budgets.models import get_budget_alerts, get_budget_alert_count
from django.utils import timezone

def budget_alerts_processor(request):
    """
    Globally context processor to expose budget_alerts and budget_alert_count to all templates.
    """
    if request.user.is_authenticated:
        today = timezone.localdate()
        alerts = get_budget_alerts(request.user, today.month, today.year)
        alert_count = get_budget_alert_count(request.user, today.month, today.year)
        return {
            'budget_alerts': alerts,
            'budget_alert_count': alert_count,
        }
    return {
        'budget_alerts': [],
        'budget_alert_count': 0,
    }
