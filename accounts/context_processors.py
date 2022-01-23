from django.conf import settings

def FIDOContextProcessor(request):
    return {
        'fido_enabled': settings.FIDO2_ENABLED,
    }
