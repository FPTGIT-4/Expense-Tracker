import datetime
from django.utils import timezone

def get_analytics_date_range(request):
    """
    Parses request GET parameters to find the active date range.
    Returns: (start_date, end_date, active_filter_name)
    """
    today = timezone.localdate()
    date_filter = request.GET.get('date_filter', 'this_month').strip().lower()
    
    if date_filter == 'today':
        return today, today, 'today'
        
    elif date_filter == 'this_week':
        # Start from Monday of current week
        start = today - datetime.timedelta(days=today.weekday())
        return start, today, 'this_week'
        
    elif date_filter == 'this_month':
        start = today.replace(day=1)
        return start, today, 'this_month'
        
    elif date_filter == 'custom':
        date_from = request.GET.get('date_from', '').strip()
        date_to = request.GET.get('date_to', '').strip()
        start = today
        end = today
        
        if date_from:
            try:
                start = datetime.datetime.strptime(date_from, '%Y-%m-%d').date()
            except ValueError:
                # Fallback if parsing fails
                start = today.replace(day=1)
        else:
            start = datetime.date(2000, 1, 1)
            
        if date_to:
            try:
                end = datetime.datetime.strptime(date_to, '%Y-%m-%d').date()
            except ValueError:
                end = today
        else:
            end = today
            
        return start, end, 'custom'
        
    # Default to this month
    start = today.replace(day=1)
    return start, today, 'this_month'
