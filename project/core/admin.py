from django.contrib import admin
from core import models

# Register your models here.
admin.site.register(models.Stock)
admin.site.register(models.Holding)
admin.site.register(models.PortfolioHistory)
admin.site.register(models.UserCash)
admin.site.register(models.Trade)