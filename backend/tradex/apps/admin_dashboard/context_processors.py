from django.conf import settings


def frontend_url(request):
    return {'FRONTEND_URL': settings.FRONTEND_URL}
