from django.contrib import admin

from .models import ProfitClaim, SystemSettings


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = ('id', 'coin_rate', 'profit_enabled', 'profit_percentage', 'last_updated_at')


@admin.register(ProfitClaim)
class ProfitClaimAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user', 'amount_usdt', 'amount_coins',
        'profit_percentage', 'claimed_at',
    )
    list_filter = ('claimed_at',)
    search_fields = ('user__email', 'user__username')
    readonly_fields = (
        'user', 'amount_usdt', 'amount_coins', 'profit_percentage',
        'profit_cycle_hours', 'base_usdt_snapshot', 'claimed_at',
    )
