from django.db import models


class SystemSettings(models.Model):
    # Coin Rate Management
    coin_rate = models.DecimalField(max_digits=20, decimal_places=8, default=0.25, help_text="Price of one coin in USD. Example: 0.25 means 1 Coin = $0.25")
    currency_symbol = models.CharField(max_length=10, default='USD', help_text="Currency symbol (e.g., USD, EUR)")
    last_updated_at = models.DateTimeField(auto_now=True, help_text="Last time coin rate was updated")
    
    # Unlock Stages
    stage1_hours = models.IntegerField(default=72)
    stage1_percent = models.DecimalField(max_digits=5, decimal_places=2, default=50)
    stage2_hours = models.IntegerField(default=24)
    stage2_percent = models.DecimalField(max_digits=5, decimal_places=2, default=25)
    stage3_hours = models.IntegerField(default=24)
    stage3_percent = models.DecimalField(max_digits=5, decimal_places=2, default=25)
    
    # Purchase/Withdrawal Limits
    min_purchase = models.DecimalField(max_digits=20, decimal_places=8, default=10)
    max_purchase = models.DecimalField(max_digits=20, decimal_places=8, default=100000)
    usdt_wallet_address = models.CharField(max_length=255, default='0x0000000000000000000000000000000000000000')
    sponsor_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=5)

    # Profit / reward system (admin-controlled)
    profit_enabled = models.BooleanField(default=False, help_text='Enable profit display and reward cycle for users')
    profit_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text='Profit percentage applied to assigned purchase USDT, e.g. 10 = 10%',
    )
    profit_cycle_hours = models.IntegerField(
        default=72,
        help_text='Hours after coin assignment before each profit reward cycle',
    )

    # Global coin supply tracking
    total_coin_supply = models.DecimalField(max_digits=30, decimal_places=8, default=21000000)
    sold_coins = models.DecimalField(max_digits=30, decimal_places=8, default=0)

    class Meta:
        verbose_name = 'System Settings'
        verbose_name_plural = 'System Settings'

    @classmethod
    def get_settings(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
    
    def calculate_coins_from_usd(self, usd_amount):
        """
        Calculate number of coins from USD amount based on coin_rate
        Example: USD 100 with rate 0.25 = 400 coins
        """
        if self.coin_rate == 0:
            return 0
        from decimal import Decimal
        usd_decimal = Decimal(str(usd_amount))
        coin_rate_decimal = Decimal(str(self.coin_rate))
        return usd_decimal / coin_rate_decimal
    
    def calculate_usd_from_coins(self, coin_amount):
        """
        Calculate USD amount from coins based on coin_rate
        """
        from decimal import Decimal
        coin_decimal = Decimal(str(coin_amount))
        rate_decimal = Decimal(str(self.coin_rate))
        return coin_decimal * rate_decimal

    @property
    def remaining_coins(self):
        from decimal import Decimal

        try:
            total_supply = Decimal(str(self.total_coin_supply or 0))
            sold = Decimal(str(self.sold_coins or 0))
            return total_supply - sold
        except Exception:
            return Decimal('0')

    def __str__(self):
        return f'System Settings (Rate: 1 Coin = ${self.coin_rate} {self.currency_symbol})'
