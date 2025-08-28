# serializers.py
from rest_framework import serializers
from django.db.models import F, Q, Sum, Avg
from .models import *
from datetime import datetime, timedelta

# 기본 Serializers
class TCGGameSerializer(serializers.ModelSerializer):
    card_count = serializers.SerializerMethodField()
    
    class Meta:
        model = TCGGame
        fields = ['id', 'name', 'name_kr', 'slug', 'is_active', 'card_count']
    
    def get_card_count(self, obj):
        return obj.cards.count()


class CardSetSerializer(serializers.ModelSerializer):
    game_name = serializers.CharField(source='game.name_kr', read_only=True)
    
    class Meta:
        model = CardSet
        fields = ['id', 'game', 'game_name', 'set_code', 'name', 'name_kr', 
                  'name_jp', 'release_date', 'is_active']


class RaritySerializer(serializers.ModelSerializer):
    class Meta:
        model = Rarity
        fields = ['id', 'game', 'rarity_code', 'rarity_name', 'rarity_name_kr', 'sort_order']


# 카드 관련 Serializers
class CardSimpleSerializer(serializers.ModelSerializer):
    """리스트용 간단한 카드 정보"""
    game_name = serializers.CharField(source='game.name_kr', read_only=True)
    set_name = serializers.CharField(source='set.name_kr', read_only=True)
    full_code = serializers.CharField(read_only=True)
    
    class Meta:
        model = Card
        fields = ['id', 'game_name', 'set_name', 'card_number', 'full_code', 
                  'name', 'name_kr', 'image_url']


class PriceSerializer(serializers.ModelSerializer):
    current_price = serializers.DecimalField(max_digits=10, decimal_places=0, read_only=True)
    discount_percentage = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Price
        fields = ['buy_price', 'sell_price', 'special_price', 'special_price_start_date',
                  'special_price_end_date', 'online_price', 'is_negotiable', 
                  'current_price', 'discount_percentage', 'updated_at']


class InventorySerializer(serializers.ModelSerializer):
    available_quantity = serializers.IntegerField(read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Inventory
        fields = ['quantity', 'reserved_quantity', 'available_quantity', 
                  'location', 'min_stock_level', 'is_low_stock', 'last_restock_date']


class CardVersionListSerializer(serializers.ModelSerializer):
    """카드 버전 리스트용"""
    card_info = CardSimpleSerializer(source='card', read_only=True)
    rarity_code = serializers.CharField(source='rarity.rarity_code', read_only=True)
    price = PriceSerializer(read_only=True)
    inventory = InventorySerializer(read_only=True)
    full_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = CardVersion
        fields = ['id', 'card_info', 'rarity_code', 'version_code', 'version_name',
                  'display_code', 'full_name', 'image_url_small', 'is_foil', 
                  'is_promo', 'price', 'inventory']


class CardVersionDetailSerializer(serializers.ModelSerializer):
    """카드 버전 상세 정보"""
    card = CardSimpleSerializer(read_only=True)
    rarity = RaritySerializer(read_only=True)
    price = PriceSerializer(read_only=True)
    inventory = InventorySerializer(read_only=True)
    aliases = serializers.StringRelatedField(many=True, read_only=True)
    market_price = serializers.SerializerMethodField()
    price_trend = serializers.SerializerMethodField()
    
    class Meta:
        model = CardVersion
        fields = '__all__'
    
    def get_market_price(self, obj):
        """최신 시장 가격"""
        try:
            market = obj.market_prices.latest('last_updated')
            return {
                'cardmarket': market.cardmarket_price,
                'bunjang_avg': market.bunjang_avg_price,
                'online_lowest': market.online_lowest_price,
                'last_updated': market.last_updated
            }
        except MarketPrice.DoesNotExist:
            return None
    
    def get_price_trend(self, obj):
        """최근 7일 가격 추이"""
        seven_days_ago = datetime.now().date() - timedelta(days=7)
        trends = obj.daily_prices.filter(date__gte=seven_days_ago).order_by('date')
        return [{
            'date': trend.date,
            'avg_price': trend.avg_price,
            'min_price': trend.min_price,
            'max_price': trend.max_price,
            'closing_price': trend.closing_price,
            'sales_count': trend.sales_count
        } for trend in trends]


class CardDetailSerializer(serializers.ModelSerializer):
    """카드 상세 정보 (모든 버전 포함)"""
    game = TCGGameSerializer(read_only=True)
    set = CardSetSerializer(read_only=True)
    versions = CardVersionListSerializer(many=True, read_only=True)
    
    class Meta:
        model = Card
        fields = '__all__'


# 재고 관리 Serializers
class InventoryLogSerializer(serializers.ModelSerializer):
    card_version_name = serializers.CharField(source='card_version.full_name', read_only=True)
    transaction_type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)
    
    class Meta:
        model = InventoryLog
        fields = ['id', 'card_version', 'card_version_name', 'transaction_type',
                  'transaction_type_display', 'quantity_change', 'quantity_after',
                  'price', 'total_amount', 'transaction_id', 'customer_info',
                  'notes', 'staff_name', 'created_at']


class StockAdjustmentSerializer(serializers.Serializer):
    """재고 조정용"""
    card_version_id = serializers.IntegerField()
    quantity_change = serializers.IntegerField()
    reason = serializers.CharField(max_length=200, required=False)
    
    def validate_card_version_id(self, value):
        try:
            CardVersion.objects.get(id=value)
        except CardVersion.DoesNotExist:
            raise serializers.ValidationError("카드 버전을 찾을 수 없습니다.")
        return value


class BulkStockUpdateSerializer(serializers.Serializer):
    """대량 재고 업데이트"""
    updates = StockAdjustmentSerializer(many=True)
    
    def create(self, validated_data):
        results = []
        for item in validated_data['updates']:
            card_version = CardVersion.objects.get(id=item['card_version_id'])
            inventory = card_version.inventory
            success = inventory.adjust_stock(
                item['quantity_change'],
                item.get('reason', '대량 재고 조정'),
                self.context.get('request').user if self.context.get('request') else None
            )
            results.append({
                'card_version_id': item['card_version_id'],
                'success': success,
                'new_quantity': inventory.quantity
            })
        return results


# 가격 관리 Serializers
class PriceUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Price
        fields = ['buy_price', 'sell_price', 'special_price', 
                  'special_price_start_date', 'special_price_end_date',
                  'online_price', 'is_negotiable']


class PriceHistorySerializer(serializers.ModelSerializer):
    card_version_name = serializers.CharField(source='card_version.full_name', read_only=True)
    
    class Meta:
        model = PriceHistory
        fields = '__all__'


class DailyPriceHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyPriceHistory
        fields = ['date', 'avg_price', 'min_price', 'max_price', 
                  'closing_price', 'sales_count', 'total_quantity']


# 검색 및 필터 Serializers
class CardSearchSerializer(serializers.Serializer):
    """카드 검색용"""
    q = serializers.CharField(required=False, allow_blank=True)  # 검색어
    game = serializers.CharField(required=False)  # 게임 slug
    set_code = serializers.CharField(required=False)
    rarity = serializers.CharField(required=False)
    min_price = serializers.DecimalField(max_digits=10, decimal_places=0, required=False)
    max_price = serializers.DecimalField(max_digits=10, decimal_places=0, required=False)
    in_stock = serializers.BooleanField(required=False)
    is_foil = serializers.BooleanField(required=False)
    is_promo = serializers.BooleanField(required=False)


# 판매 관련 Serializers
class SaleItemSerializer(serializers.Serializer):
    """판매 아이템"""
    card_version_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    price = serializers.DecimalField(max_digits=10, decimal_places=0)


class SaleSerializer(serializers.Serializer):
    """판매 처리"""
    items = SaleItemSerializer(many=True)
    customer_info = serializers.CharField(max_length=200, required=False)
    payment_method = serializers.CharField(max_length=50, required=False)
    transaction_id = serializers.CharField(max_length=50, required=False)
    notes = serializers.CharField(required=False)
    
    def create(self, validated_data):
        items = validated_data['items']
        customer_info = validated_data.get('customer_info', '')
        transaction_id = validated_data.get('transaction_id', '')
        notes = validated_data.get('notes', '')
        
        logs = []
        total_amount = 0
        
        for item in items:
            card_version = CardVersion.objects.get(id=item['card_version_id'])
            inventory = card_version.inventory
            
            # 재고 확인
            if inventory.available_quantity < item['quantity']:
                raise serializers.ValidationError(
                    f"{card_version.full_name}의 재고가 부족합니다."
                )
            
            # 재고 차감
            inventory.quantity -= item['quantity']
            inventory.save()
            
            # 판매 로그 생성
            log = InventoryLog.objects.create(
                card_version=card_version,
                transaction_type='OUT',
                quantity_change=-item['quantity'],
                quantity_after=inventory.quantity,
                price=item['price'],
                total_amount=item['price'] * item['quantity'],
                transaction_id=transaction_id,
                customer_info=customer_info,
                notes=notes,
                staff_name=str(self.context.get('request').user) if self.context.get('request') else ''
            )
            logs.append(log)
            total_amount += item['price'] * item['quantity']
            
            # 일별 판매 기록 업데이트
            today = datetime.now().date()
            daily_price, created = DailyPriceHistory.objects.get_or_create(
                card_version=card_version,
                date=today,
                defaults={'closing_price': item['price']}
            )
            daily_price.sales_count += 1
            daily_price.total_quantity += item['quantity']
            daily_price.save()
        
        return {
            'transaction_id': transaction_id,
            'total_amount': total_amount,
            'items_sold': len(items),
            'logs': logs
        }


# 통계 Serializers
class InventoryStatSerializer(serializers.Serializer):
    """재고 통계"""
    total_cards = serializers.IntegerField()
    total_quantity = serializers.IntegerField()
    total_value = serializers.DecimalField(max_digits=12, decimal_places=0)
    low_stock_items = serializers.IntegerField()
    out_of_stock_items = serializers.IntegerField()


class SalesStatSerializer(serializers.Serializer):
    """매출 통계"""
    period = serializers.CharField()  # daily, weekly, monthly
    total_sales = serializers.DecimalField(max_digits=12, decimal_places=0)
    total_transactions = serializers.IntegerField()
    total_quantity_sold = serializers.IntegerField()
    top_selling_cards = serializers.ListField()