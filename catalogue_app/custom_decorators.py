from functools import wraps
from django.http import HttpResponseForbidden


def authority_required(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        if request.user.user_role.role_name not in ['admin', 'moderator']:
            return HttpResponseForbidden()
        return func(request, *args, **kwargs)
    return wrapper
