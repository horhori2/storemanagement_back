# models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.db.models import F, Q, Sum
from django.contrib.auth.models import User
from decimal import Decimal
import json

# 1. TCG 게임 종류 모델
class TCGGame(models.Model):
    name = models.CharField(max_length=50, unique=True)
    name_kr = models.CharField(max_length=50, blank=True, null=True)
    slug = models.SlugField(max_length=50, unique=True, blank=True, null=True)
    is_active = models.BooleanField(default=True)  # 이미 default=True가 있음
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tcg_games'
        verbose_name = 'TCG Game'
        verbose_name_plural = 'TCG Games'
        ordering = ['name']
    
    def __str__(self):
        return self.name_kr or self.name


# 2. 카드 세트/확장팩 모델
class CardSet(models.Model):
    game = models.ForeignKey(TCGGame, on_delete=models.CASCADE, related_name='sets')
    set_code = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    name_kr = models.CharField(max_length=100, blank=True, null=True)
    name_jp = models.CharField(max_length=100, blank=True, null=True)
    release_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)  # DEFAULT TRUE 추가
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'card_sets'
        verbose_name = 'Card Set'
        verbose_name_plural = 'Card Sets'
        unique_together = ['game', 'set_code']
        ordering = ['-release_date', 'name']
        indexes = [
            models.Index(fields=['set_code']),
            models.Index(fields=['release_date']),
        ]
    
    def __str__(self):
        return f"[{self.set_code}] {self.name_kr or self.name}"


# 3. 카드 희귀도 모델
class Rarity(models.Model):
    game = models.ForeignKey(TCGGame, on_delete=models.CASCADE, related_name='rarities')
    rarity_code = models.CharField(max_length=20)
    rarity_name = models.CharField(max_length=50)
    rarity_name_kr = models.CharField(max_length=50, blank=True, null=True)
    sort_order = models.IntegerField(default=0)  # 이미 default=0이 있음
    
    class Meta:
        db_table = 'rarities'
        verbose_name = 'Rarity'
        verbose_name_plural = 'Rarities'
        unique_together = ['game', 'rarity_code']
        ordering = ['sort_order', 'rarity_code']
        indexes = [
            models.Index(fields=['rarity_code']),
        ]
    
    def __str__(self):
        return f"{self.rarity_code} - {self.rarity_name_kr or self.rarity_name}"


# 4. 메인 카드 모델
class Card(models.Model):
    game = models.ForeignKey(TCGGame, on_delete=models.CASCADE, related_name='cards')
    set = models.ForeignKey(CardSet, on_delete=models.CASCADE, related_name='cards')
    card_number = models.CharField(max_length=30)  # 기존: OP01-001
    data_number = models.CharField(max_length=50, null=True, blank=True)  # 신규: 고유 식별자
    name = models.CharField(max_length=200)
    name_kr = models.CharField(max_length=200, blank=True, null=True)
    name_jp = models.CharField(max_length=200, blank=True, null=True)
    image_url = models.URLField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cards'
        verbose_name = 'Card'
        verbose_name_plural = 'Cards'
        constraints = [
           models.UniqueConstraint(
               fields=['game', 'set', 'data_number'],
               condition=models.Q(data_number__isnull=False),
               name='unique_card_with_data_number'
           )
       ]
        ordering = ['set', 'card_number']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['card_number']),
        ]
    
    def __str__(self):
        return f"[{self.card_number}] {self.name_kr or self.name}"
    
    @property
    def full_code(self):
        return f"{self.set.set_code}-{self.card_number}"


# 5. 카드 버전 모델
class CardVersion(models.Model):
    VERSION_CHOICES = [
        ('normal', 'Normal'),
        ('parallel', 'Parallel'),
        ('secret', 'Secret'),
        ('alt-art', 'Alternate Art'),
        ('aa', 'AA'),
        ('sp', 'Special'),
        ('promo', 'Promo'),
    ]
    
    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name='versions')
    rarity = models.ForeignKey(Rarity, on_delete=models.SET_NULL, null=True, related_name='card_versions')
    version_code = models.CharField(max_length=50, choices=VERSION_CHOICES, default='normal')
    version_name = models.CharField(max_length=100, blank=True, null=True)
    display_code = models.CharField(max_length=20, blank=True, null=True)  # AA, SP, SR+ 등
    
    image_url = models.URLField(max_length=500, blank=True, null=True)
    image_url_small = models.URLField(max_length=500, blank=True, null=True)
    
    is_foil = models.BooleanField(default=False)  # 이미 default=False가 있음
    is_promo = models.BooleanField(default=False)  # 이미 default=False가 있음
    is_alternate_art = models.BooleanField(default=False)
    
    market_code = models.CharField(max_length=50, blank=True, null=True)  # 외부 마켓 연동용
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'card_versions'
        verbose_name = 'Card Version'
        verbose_name_plural = 'Card Versions'
        unique_together = ['card', 'rarity', 'version_code']
        ordering = ['card', 'rarity__sort_order']
        indexes = [
            models.Index(fields=['card']),
            models.Index(fields=['rarity']),
        ]
    
    def __str__(self):
        display = f"{self.card.full_code}"
        if self.display_code:
            display += f" {self.display_code}"
        elif self.version_name:
            display += f" ({self.version_name})"
        return display
    
    @property
    def full_name(self):
        name = self.card.name_kr or self.card.name
        if self.version_name:
            name += f" - {self.version_name}"
        return name


# 6. 재고 관리 모델
class Inventory(models.Model):
    card_version = models.OneToOneField(CardVersion, on_delete=models.CASCADE, related_name='inventory')
    quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])  # 이미 default=0이 있음
    reserved_quantity = models.IntegerField(default=0, validators=[MinValueValidator(0)])  # 이미 default=0이 있음
    location = models.CharField(max_length=50, blank=True, null=True)
    min_stock_level = models.IntegerField(default=0)  # 이미 default=0이 있음
    last_restock_date = models.DateField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'inventory'
        verbose_name = 'Inventory'
        verbose_name_plural = 'Inventories'
        indexes = [
            models.Index(fields=['quantity']),
            models.Index(fields=['updated_at']),
        ]
    
    def __str__(self):
        return f"{self.card_version} - 재고: {self.available_quantity}/{self.quantity}"
    
    @property
    def available_quantity(self):
        return max(0, self.quantity - self.reserved_quantity)
    
    @property
    def is_low_stock(self):
        return self.available_quantity <= self.min_stock_level
    
    def reserve(self, quantity):
        """재고 예약"""
        if self.available_quantity >= quantity:
            self.reserved_quantity = F('reserved_quantity') + quantity
            self.save(update_fields=['reserved_quantity'])
            return True
        return False
    
    def release_reservation(self, quantity):
        """예약 해제"""
        self.reserved_quantity = max(0, F('reserved_quantity') - quantity)
        self.save(update_fields=['reserved_quantity'])
    
    def adjust_stock(self, quantity_change, reason='', staff=None):
        """재고 조정"""
        new_quantity = self.quantity + quantity_change
        if new_quantity < 0:
            raise ValueError("재고가 음수가 될 수 없습니다.")
        
        old_quantity = self.quantity
        self.quantity = new_quantity
        self.save()
        
        # 로그 생성
        InventoryLog.objects.create(
            card_version=self.card_version,
            transaction_type='ADJUST',
            quantity_change=quantity_change,
            quantity_after=new_quantity,
            notes=reason,
            staff_name=str(staff) if staff else ''
        )
        
        return True


# 7. 가격 정보 모델
class Price(models.Model):
    card_version = models.OneToOneField(CardVersion, on_delete=models.CASCADE, related_name='price')
    
    buy_price = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True)
    # 기본값을 0으로 설정하여 None 방지
    sell_price = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    
    special_price = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True)
    special_price_start_date = models.DateTimeField(null=True, blank=True)
    special_price_end_date = models.DateTimeField(null=True, blank=True)
    
    online_price = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True)
    
    is_negotiable = models.BooleanField(default=False)  # 이미 default=False가 있음
    
    updated_at = models.DateTimeField(auto_now=True)

    
    
    class Meta:
        db_table = 'prices'
        verbose_name = 'Price'
        verbose_name_plural = 'Prices'
        indexes = [
            models.Index(fields=['sell_price']),
            models.Index(fields=['updated_at']),
        ]
    
    def __str__(self):
        return f"{self.card_version} - ₩{self.current_price:,}"
    
    @property
    def current_price(self):
        """현재 적용 가격 (세일 가격 우선)"""
        now = timezone.now()
        
        # 특가 정보가 모두 있을 때만 비교
        if (self.special_price is not None and 
            self.special_price_start_date is not None and 
            self.special_price_end_date is not None):
            
            # 특가 기간 내인지 확인
            if self.special_price_start_date <= now <= self.special_price_end_date:
                return self.special_price
        
        return self.sell_price

    @property
    def discount_percentage(self):
        """할인율"""
        if self.current_price and self.sell_price and self.current_price < self.sell_price:
            return int((1 - self.current_price / self.sell_price) * 100)
        return 0


# 8. 재고 변동 로그 모델
class InventoryLog(models.Model):
    TRANSACTION_TYPES = [
        ('IN', '입고'),
        ('OUT', '판매'),
        ('ADJUST', '조정'),
        ('RETURN', '반품'),
    ]
    
    card_version = models.ForeignKey(CardVersion, on_delete=models.CASCADE, related_name='inventory_logs')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    quantity_change = models.IntegerField()
    quantity_after = models.IntegerField()
    
    price = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True)
    
    transaction_id = models.CharField(max_length=50, blank=True, null=True)
    customer_info = models.CharField(max_length=200, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    staff_name = models.CharField(max_length=50, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'inventory_logs'
        verbose_name = 'Inventory Log'
        verbose_name_plural = 'Inventory Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['card_version']),
            models.Index(fields=['transaction_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.card_version} ({self.quantity_change:+})"


# 9. 가격 변동 히스토리 모델
class PriceHistory(models.Model):
    card_version = models.ForeignKey(CardVersion, on_delete=models.CASCADE, related_name='price_history')
    
    old_buy_price = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True)
    new_buy_price = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True)
    old_sell_price = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True)
    new_sell_price = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True)
    
    change_reason = models.CharField(max_length=200, blank=True, null=True)
    changed_by = models.CharField(max_length=50, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'price_history'
        verbose_name = 'Price History'
        verbose_name_plural = 'Price Histories'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['card_version']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.card_version} - {self.old_sell_price} → {self.new_sell_price}"


# 10. 일별 가격 히스토리 모델 (그래프용)
# 기존 DailyPriceHistory 모델 수정 (방법 2)
class DailyPriceHistory(models.Model):
    card_version = models.ForeignKey(CardVersion, on_delete=models.CASCADE, related_name='daily_prices')
    date = models.DateField()
    
    # 그래프용 최저가 필드 (네이버 쇼핑 등에서 검색한 최저가)
    online_lowest_price = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True)
    
    # 기존 필드들은 선택사항으로 유지 (다른 용도로 활용 가능)
    avg_price = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True)
    min_price = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True)
    max_price = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True)
    closing_price = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True)
    
    sales_count = models.IntegerField(default=0)
    total_quantity = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'daily_price_history'
        verbose_name = 'Daily Price History'
        verbose_name_plural = 'Daily Price Histories'
        unique_together = ['card_version', 'date']
        ordering = ['-date']
        indexes = [
            models.Index(fields=['card_version', 'date']),
            models.Index(fields=['date']),
        ]
    
    def __str__(self):
        return f"{self.card_version} - {self.date}: {self.online_lowest_price}원"

# 11. 카드 버전 별칭 모델 (검색 최적화)
class CardVersionAlias(models.Model):
    ALIAS_TYPES = [
        ('code', 'Code'),
        ('name', 'Name'),
        ('nickname', 'Nickname'),
    ]
    
    card_version = models.ForeignKey(CardVersion, on_delete=models.CASCADE, related_name='aliases')
    alias = models.CharField(max_length=100)
    alias_type = models.CharField(max_length=10, choices=ALIAS_TYPES, default='nickname')  # DEFAULT 'nickname' 추가
    
    class Meta:
        db_table = 'card_version_aliases'
        verbose_name = 'Card Version Alias'
        verbose_name_plural = 'Card Version Aliases'
        indexes = [
            models.Index(fields=['alias']),
            models.Index(fields=['card_version']),
        ]
    
    def __str__(self):
        return f"{self.alias} → {self.card_version}"


# 12. 시장 가격 참조 모델
class MarketPrice(models.Model):
    card_version = models.ForeignKey(CardVersion, on_delete=models.CASCADE, related_name='market_prices')
    
    cardmarket_price = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True)
    bunjang_avg_price = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True)
    online_lowest_price = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True)
    
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'market_prices'
        verbose_name = 'Market Price'
        verbose_name_plural = 'Market Prices'
        indexes = [
            models.Index(fields=['card_version']),
            models.Index(fields=['last_updated']),
        ]
    
    def __str__(self):
        return f"{self.card_version} - Market Price"


# Signal handlers
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

@receiver(pre_save, sender=Price)
def create_price_history(sender, instance, **kwargs):
    """가격 변경시 히스토리 자동 생성"""
    if instance.pk:
        try:
            old_price = Price.objects.get(pk=instance.pk)
            if old_price.sell_price != instance.sell_price or old_price.buy_price != instance.buy_price:
                PriceHistory.objects.create(
                    card_version=instance.card_version,
                    old_buy_price=old_price.buy_price,
                    new_buy_price=instance.buy_price,
                    old_sell_price=old_price.sell_price,
                    new_sell_price=instance.sell_price
                )
                
                # 일별 가격 업데이트
                today = timezone.now().date()
                daily_price, created = DailyPriceHistory.objects.get_or_create(
                    card_version=instance.card_version,
                    date=today,
                    defaults={
                        'closing_price': instance.sell_price,
                        'avg_price': instance.sell_price,
                        'min_price': instance.sell_price,
                        'max_price': instance.sell_price,
                    }
                )
                
                if not created:
                    daily_price.closing_price = instance.sell_price
                    if daily_price.min_price:
                        daily_price.min_price = min(daily_price.min_price, instance.sell_price)
                    if daily_price.max_price:
                        daily_price.max_price = max(daily_price.max_price, instance.sell_price)
                    daily_price.save()
                    
        except Price.DoesNotExist:
            pass


@receiver(post_save, sender=CardVersion)
def create_inventory_and_price(sender, instance, created, **kwargs):
    """카드 버전 생성시 재고와 가격 자동 생성"""
    if created:
        Inventory.objects.get_or_create(card_version=instance)
        Price.objects.get_or_create(
            card_version=instance,
            defaults={
                'sell_price': 0,  # 기본 판매가격 0
                'buy_price': 0,   # 기본 매입가격 0
            }
        )