from rest_framework import serializers

from .models import ProfitClaim, SystemSettings


class SystemSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemSettings
        fields = [
            'coin_rate', 'currency_symbol', 'last_updated_at',
            'stage1_hours', 'stage1_percent',
            'stage2_hours', 'stage2_percent',
            'stage3_hours', 'stage3_percent',
            'min_purchase', 'max_purchase',
            'usdt_wallet_address', 'sponsor_percentage', 'sponsor_access_fee_usdt',
            'sponsor_reward_threshold_usdt',
            'profit_enabled', 'profit_percentage', 'profit_cycle_hours',
            'total_coin_supply', 'sold_coins',
            'remaining_coins',
        ]

    def validate_profit_percentage(self, value):
        if value is not None and (value < 0 or value > 100):
            raise serializers.ValidationError(
                'Profit percentage must be between 0 and 100.',
            )
        return value

    def validate_profit_cycle_hours(self, value):
        if value is not None and value < 1:
            raise serializers.ValidationError(
                'Profit cycle hours must be at least 1.',
            )
        return value


class ProfitClaimSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProfitClaim
        fields = [
            'id',
            'amount_usdt',
            'amount_coins',
            'profit_percentage',
            'profit_cycle_hours',
            'base_usdt_snapshot',
            'claimed_at',
        ]
        read_only_fields = fields
