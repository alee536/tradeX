from django.contrib import admin
from .models import SponsorAccessRequest, SponsorEarning


@admin.register(SponsorEarning)
class SponsorEarningAdmin(admin.ModelAdmin):
    list_display = ('sponsor', 'sponsored_user', 'amount_display', 'source_type', 'created_at')
    list_filter = ('source_type', 'created_at')
    search_fields = ('sponsor__username', 'sponsored_user__username')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Earning Info', {
            'fields': ('sponsor', 'sponsored_user', 'amount', 'source_type', 'created_at')
        }),
    )
    
    def amount_display(self, obj):
        return f"{obj.amount} tokens"
    amount_display.short_description = "Amount"
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('sponsor', 'sponsored_user')


@admin.register(SponsorAccessRequest)
class SponsorAccessRequestAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user', 'ref_slug', 'status', 'payment_status',
        'fee_usdt', 'created_at',
    )
    list_filter = ('status', 'payment_status', 'created_at')
    search_fields = ('user__username', 'user__email', 'ref_slug', 'payment_txid')
    readonly_fields = ('created_at', 'reviewed_at', 'activated_at')
