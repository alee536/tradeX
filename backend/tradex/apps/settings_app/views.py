from django.conf import settings as django_settings
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.sponsor.access import get_sponsor_access_fee

from .models import ProfitClaim, SystemSettings
from .profit import ProfitClaimError, compute_user_profit_summary, execute_profit_claim
from .serializers import ProfitClaimSerializer, SystemSettingsSerializer


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


class AdminSettingsView(APIView):
    """============== Admin system settings (read / update) =============="""

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        settings = SystemSettings.get_settings()
        return Response(SystemSettingsSerializer(settings).data)

    def patch(self, request):
        settings_obj = SystemSettings.get_settings()
        serializer = SystemSettingsSerializer(
            settings_obj,
            data=request.data,
            partial=True,
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PublicSettingsView(APIView):
    """============== Public settings for SPA (no auth) =============="""

    permission_classes = [AllowAny]

    def get(self, request):
        settings = SystemSettings.get_settings()
        payload = {
            'coin_rate': settings.coin_rate,
            'currency_symbol': settings.currency_symbol,
            'last_updated_at': settings.last_updated_at,
            'min_purchase': settings.min_purchase,
            'max_purchase': settings.max_purchase,
            'total_coin_supply': settings.total_coin_supply,
            'profit_percentage': settings.profit_percentage,
            'usdt_wallet_address': django_settings.USDT_PURCHASE_WALLET_ADDRESS,
            'sponsor_payment_wallet_address': django_settings.SPONSOR_PAYMENT_WALLET_ADDRESS,
            'sponsor_access_fee_usdt': float(get_sponsor_access_fee()),
        }
        payload.update(_profit_public_fields(settings))
        return Response(payload)


class PublicPriceView(APIView):
    """============== Public coin price endpoint =============="""

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


class ProfitClaimView(APIView):
    """============== Claim profit reward for current cycle =============="""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            summary = execute_profit_claim(request.user)
        except ProfitClaimError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'message': 'Profit reward claimed successfully.',
            'profit': summary,
        }, status=status.HTTP_201_CREATED)


class ProfitClaimHistoryView(APIView):
    """============== User profit claim history =============="""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        claims = ProfitClaim.objects.filter(user=request.user).order_by('-claimed_at')[:50]
        return Response(ProfitClaimSerializer(claims, many=True).data)


# Backward-compatible callables for URL includes that reference function names.
get_settings = AdminSettingsView.as_view()
update_settings = AdminSettingsView.as_view()
public_settings = PublicSettingsView.as_view()
public_price = PublicPriceView.as_view()
