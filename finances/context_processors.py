from finances.models import NotificationReminder


def notifications_context(request):
    """
    Supplies all recent notifications (both unread and read history)
    and unread count so users can scroll and view their recent alerts history.
    """
    if request.user.is_authenticated:
        unread_count = NotificationReminder.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        recent_notifications = NotificationReminder.objects.filter(
            user=request.user
        ).order_by('-created_at')[:30]
        return {
            'recent_notifications': recent_notifications,
            'unread_notifications_count': unread_count,
        }
    return {
        'recent_notifications': [],
        'unread_notifications_count': 0,
    }
