import zoneinfo
from django.utils import timezone


class TimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            user_timezone = request.COOKIES.get('django_timezone') or 'UTC'
            if user_timezone:
                timezone.activate(zoneinfo.ZoneInfo(user_timezone))
            else:
                timezone.deactivate()
        except:
            timezone.deactivate()

        return self.get_response(request)
