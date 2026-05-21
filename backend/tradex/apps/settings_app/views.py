from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SystemSettings
from .serializers import SystemSettingsSerializer


class AdminSettingsView(APIView):
    """Staff-only system settings (GET / PATCH)."""

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        settings = SystemSettings.get_settings()
        return Response(SystemSettingsSerializer(settings).data)

    def patch(self, request):
        settings_obj = SystemSettings.get_settings()
        serializer = SystemSettingsSerializer(settings_obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


class PublicSettingsView(APIView):
    """Public purchase-related settings (no auth)."""

    permission_classes = [AllowAny]

    def get(self, request):
        settings = SystemSettings.get_settings()
        payload = {
            'coin_rate': settings.coin_rate,
            'currency_symbol': settings.currency_symbol,
            'last_updated_at': settings.last_updated_at,
            'min_purchase': settings.min_purchase,
            'max_purchase': settings.max_purchase,
            'usdt_wallet_address': settings.usdt_wallet_address,
        }
        if settings.profit_enabled:
            payload['profit_enabled'] = True
            payload['profit_percentage'] = settings.profit_percentage
            payload['profit_cycle_hours'] = settings.profit_cycle_hours
        else:
            payload['profit_enabled'] = False
        return Response(payload)


class PublicPriceView(APIView):
    """Lightweight public coin price endpoint."""

    permission_classes = [AllowAny]

    def get(self, request):
        settings = SystemSettings.get_settings()
        return Response({
            'price': settings.coin_rate,
            'currency': settings.currency_symbol,
            'last_updated_at': settings.last_updated_at,
            'change_24h_percent': None,
            'source': 'settings',
        })
