from django.db import models
from django.conf import settings
from django.utils import timezone

# Create your models here.
class Stock(models.Model):
    symbol = models.CharField(max_length=5, unique=True)
    desc = models.TextField()

    def __str__(self):
        return f"{self.symbol}"

class Trade(models.Model):
    class TradeType(models.TextChoices):
        BUY = "BUY", "Buy"
        SELL = "SELL", "Sell"
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="trades",
    )

    date = models.DateTimeField(default=timezone.now, db_index=True)
    trade_type = models.CharField(max_length=4, choices=TradeType.choices)

    stock = models.ForeignKey(
        Stock,
        on_delete=models.CASCADE,
        related_name="trades",
    )

    shares = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["date"]

    def __str__(self):
        return f"{self.user.username} {self.date} {self.stock.symbol} {self.shares} {self.price}"
    
class Holding(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="holdings",
    )

    symbol = models.CharField(max_length=5)
    shares = models.PositiveIntegerField()

    class Meta:
        unique_together = ('user', 'symbol')

    def __str__(self):
        return f"{self.user.username} {self.symbol} {self.shares}"

class UserCash(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user_cash"
    )

    cash = models.DecimalField(max_digits=12, decimal_places=2, default=10_000)

    def __str__(self):
        return f"{self.user.username} ${self.cash:.2f}"
    
class PortfolioHistory(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="portfolio_history"
    )

    value = models.DecimalField(max_digits=12, decimal_places=2, default=10_000)
    date = models.DateField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ['date']
        unique_together = ('user', 'date')

    def __str__(self):
        return f"{self.user.username} {self.value} {self.date}"