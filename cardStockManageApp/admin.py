from django.contrib import admin
from .models import TCGGame, CardSet, Rarity, Card, CardVersion, Inventory, Price, InventoryLog, PriceHistory, DailyPriceHistory, CardVersionAlias, MarketPrice

# Register your models here.
admin.site.register(TCGGame)
admin.site.register(CardSet)
admin.site.register(Rarity)
admin.site.register(Card)
admin.site.register(CardVersion)
admin.site.register(Inventory)
admin.site.register(Price)
admin.site.register(InventoryLog)
admin.site.register(PriceHistory)
admin.site.register(DailyPriceHistory)
admin.site.register(CardVersionAlias)
admin.site.register(MarketPrice)