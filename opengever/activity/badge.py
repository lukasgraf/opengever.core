from opengever.activity.dispatcher import NotificationDispatcher


class BadgeIconDispatcher(NotificationDispatcher):

    roles_key = 'badge_notification_roles'

    def dispatch_notification(self, notification):
        notification.is_badge = True
