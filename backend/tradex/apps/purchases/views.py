from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from decimal import Decimal
from .models import Purchase
from .serializers import PurchaseSerializer, PurchaseInputSerializer
from apps.notifications.utils import create_notification, notify_admins
from apps.settings_app.models import SystemSettings


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def purchases_list(request):
    if request.method == 'GET':
        qs = Purchase.objects.filter(user=request.user).order_by('-created_at')
        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = PurchaseSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    serializer = PurchaseInputSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    purchase = serializer.save(user=request.user)

    settings_obj = SystemSettings.get_settings()
    coin_rate = Decimal(str(settings_obj.coin_rate))
    calculated_coins = Decimal(str(purchase.amount)) / coin_rate if coin_rate > 0 else Decimal('0')

    purchase.coin_rate_at_approval = settings_obj.coin_rate
    purchase.approved_coin_amount = calculated_coins
    purchase.is_coins_assigned = False
    purchase.save(update_fields=['coin_rate_at_approval', 'approved_coin_amount', 'is_coins_assigned'])

    create_notification(
        request.user,
        'purchase_submitted',
        f'Your purchase request for {purchase.amount} USDT will generate {calculated_coins:.8f} coins and is pending review.'
    )
    notify_admins(
        'admin_purchase_submitted',
        f'New purchase from {request.user.email or request.user.username}: '
        f'{purchase.amount} USDT (TX: {purchase.transaction_id}). Awaiting approval.',
    )
    return Response(PurchaseSerializer(purchase).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def purchase_detail(request, pk):
    try:
        purchase = Purchase.objects.get(pk=pk, user=request.user)
    except Purchase.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
    return Response(PurchaseSerializer(purchase).data)
