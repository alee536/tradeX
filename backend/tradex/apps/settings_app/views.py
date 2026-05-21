from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from .models import SystemSettings
from .serializers import SystemSettingsSerializer


def _profit_public_fields(settings):
    """Avoid breaking public API if profit migration not applied yet."""
    try:
        if settings.profit_enabled:
            return {
                'profit_enabled': True,
                'profit_percentage': settings.profit_percentage,
                'profit_cycle_hours': settings.profit_cycle_hours,
            }
    except Exception:
        pass
    return {'profit_enabled': False}


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def get_settings(request):
    settings = SystemSettings.get_settings()
    return Response(SystemSettingsSerializer(settings).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def public_settings(request):
    settings = SystemSettings.get_settings()
    payload = {
        'coin_rate': settings.coin_rate,
        'currency_symbol': settings.currency_symbol,
        'last_updated_at': settings.last_updated_at,
        'min_purchase': settings.min_purchase,
        'max_purchase': settings.max_purchase,
        'usdt_wallet_address': settings.usdt_wallet_address,
    }
    payload.update(_profit_public_fields(settings))
    return Response(payload)


@api_view(['GET'])
@permission_classes([AllowAny])
def public_price(request):
    settings = SystemSettings.get_settings()
    return Response({
        'price': settings.coin_rate,
        'currency': settings.currency_symbol,
        'last_updated_at': settings.last_updated_at,
        'change_24h_percent': None,
        'source': 'settings',
    })


@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsAdminUser])
def update_settings(request):
    settings_obj = SystemSettings.get_settings()
    serializer = SystemSettingsSerializer(settings_obj, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=400)
