from django.utils import timezone
from .utils import generate_recurring_transactions

class RecurringTransactionsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            today = timezone.localdate()
            last_check = request.session.get('last_recurrence_check')
            if not last_check or last_check != today.isoformat():
                generate_recurring_transactions(request.user)
                request.session['last_recurrence_check'] = today.isoformat()
        return self.get_response(request)
