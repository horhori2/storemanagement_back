# ===== views.py =====
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, F, Sum, Count, Avg
from django.utils import timezone
from datetime import datetime, timedelta
import django_filters
from .models import CardVersion, TCGGame, Card, CardSet, Inventory, InventoryLog
from .serializers import TCGGameSerializer, CardSetSerializer, CardDetailSerializer, CardSearchSerializer, CardVersionListSerializer, CardSimpleSerializer, DailyPriceHistorySerializer, PriceUpdateSerializer, PriceHistorySerializer, CardVersionDetailSerializer, InventorySerializer, BulkStockUpdateSerializer, SaleSerializer
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView

# Custom Filters
class CardVersionFilter(django_filters.FilterSet):
    game = django_filters.CharFilter(field_name='card__game__slug')
    set_code = django_filters.CharFilter(field_name='card__set__set_code')
    rarity = django_filters.CharFilter(field_name='rarity__rarity_code')
    min_price = django_filters.NumberFilter(field_name='price__sell_price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='price__sell_price', lookup_expr='lte')
    in_stock = django_filters.BooleanFilter(method='filter_in_stock')
    is_foil = django_filters.BooleanFilter(field_name='is_foil')
    is_promo = django_filters.BooleanFilter(field_name='is_promo')
    
    class Meta:
        model = CardVersion
        fields = ['version_code', 'is_foil', 'is_promo', 'is_alternate_art']
    
    def filter_in_stock(self, queryset, name, value):
        if value:
            return queryset.filter(inventory__quantity__gt=0)
        return queryset.filter(inventory__quantity=0)


# ViewSets
class TCGGameViewSet(viewsets.ModelViewSet):
    queryset = TCGGame.objects.filter(is_active=True)
    serializer_class = TCGGameSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'


class CardSetViewSet(viewsets.ModelViewSet):
    queryset = CardSet.objects.filter(is_active=True)
    serializer_class = CardSetSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['game', 'set_code']
    ordering_fields = ['release_date', 'name']
    ordering = ['-release_date']


class CardViewSet(viewsets.ModelViewSet):
    queryset = Card.objects.all()
    serializer_class = CardDetailSerializer
    permission_classes = [AllowAny]
    filter_backends = [SearchFilter, DjangoFilterBackend, OrderingFilter]
    search_fields = ['name', 'name_kr', 'card_number']
    filterset_fields = ['game', 'set']
    ordering_fields = ['card_number', 'name']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return CardSimpleSerializer
        return CardDetailSerializer
    
    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """특정 카드의 모든 버전 조회"""
        card = self.get_object()
        versions = card.versions.all()
        serializer = CardVersionListSerializer(versions, many=True)
        return Response(serializer.data)


class CardVersionViewSet(viewsets.ModelViewSet):
    queryset = CardVersion.objects.select_related(
        'card', 'card__game', 'card__set', 'rarity', 'price', 'inventory'
    ).all()
    permission_classes = [AllowAny]
    filter_backends = [SearchFilter, DjangoFilterBackend, OrderingFilter]
    filterset_class = CardVersionFilter
    search_fields = ['card__name', 'card__name_kr', 'card__card_number', 'aliases__alias']
    ordering_fields = ['card__card_number', 'price__sell_price', 'inventory__quantity']
    ordering = ['card__set', 'card__card_number']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return CardVersionListSerializer
        elif self.action in ['price_history', 'price_trend']:
            return DailyPriceHistorySerializer
        elif self.action == 'update_price':
            return PriceUpdateSerializer
        return CardVersionDetailSerializer
    
    @action(detail=True, methods=['get'])
    def price_history(self, request, pk=None):
        """가격 변동 이력"""
        card_version = self.get_object()
        days = int(request.query_params.get('days', 30))
        start_date = datetime.now().date() - timedelta(days=days)
        
        history = card_version.price_history.filter(
            created_at__date__gte=start_date
        ).order_by('-created_at')
        
        serializer = PriceHistorySerializer(history, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def price_trend(self, request, pk=None):
        """일별 가격 추이 (그래프용)"""
        card_version = self.get_object()
        days = int(request.query_params.get('days', 30))
        start_date = datetime.now().date() - timedelta(days=days)
        
        trends = card_version.daily_prices.filter(
            date__gte=start_date
        ).order_by('date')
        
        serializer = DailyPriceHistorySerializer(trends, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def update_price(self, request, pk=None):
        """가격 업데이트"""
        card_version = self.get_object()
        price = card_version.price
        
        serializer = PriceUpdateSerializer(price, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def adjust_stock(self, request, pk=None):
        """재고 조정"""
        card_version = self.get_object()
        quantity_change = request.data.get('quantity_change', 0)
        reason = request.data.get('reason', '')
        
        try:
            inventory = card_version.inventory
            inventory.adjust_stock(quantity_change, reason, request.user)
            
            return Response({
                'success': True,
                'new_quantity': inventory.quantity,
                'available_quantity': inventory.available_quantity
            })
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class InventoryViewSet(viewsets.ModelViewSet):
    queryset = Inventory.objects.select_related('card_version').all()
    serializer_class = InventorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['location']
    ordering_fields = ['quantity', 'updated_at']
    
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """재고 부족 상품 조회"""
        low_stock_items = Inventory.objects.filter(
            quantity__lte=F('min_stock_level')
        ).select_related('card_version')
        
        data = [{
            'card_version': CardVersionListSerializer(item.card_version).data,
            'current_quantity': item.quantity,
            'min_stock_level': item.min_stock_level,
            'location': item.location
        } for item in low_stock_items]
        
        return Response(data)
    
    @action(detail=False, methods=['post'])
    def bulk_update(self, request):
        """대량 재고 업데이트"""
        serializer = BulkStockUpdateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            results = serializer.save()
            return Response(results)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """재고 통계"""
        stats = Inventory.objects.aggregate(
            total_cards=Count('id'),
            total_quantity=Sum('quantity'),
            total_value=Sum(F('quantity') * F('card_version__price__sell_price'))
        )
        
        stats['low_stock_items'] = Inventory.objects.filter(
            quantity__lte=F('min_stock_level')
        ).count()
        
        stats['out_of_stock_items'] = Inventory.objects.filter(quantity=0).count()
        
        return Response(stats)


class SaleViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def process(self, request):
        """판매 처리"""
        serializer = SaleSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            result = serializer.save()
            return Response(result, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """매출 통계"""
        period = request.query_params.get('period', 'daily')
        
        if period == 'daily':
            start_date = datetime.now().date()
        elif period == 'weekly':
            start_date = datetime.now().date() - timedelta(days=7)
        elif period == 'monthly':
            start_date = datetime.now().date() - timedelta(days=30)
        else:
            start_date = datetime.now().date()
        
        sales = InventoryLog.objects.filter(
            transaction_type='OUT',
            created_at__date__gte=start_date
        )
        
        stats = sales.aggregate(
            total_sales=Sum('total_amount'),
            total_transactions=Count('transaction_id', distinct=True),
            total_quantity_sold=Sum(F('quantity_change') * -1)
        )
        
        # 베스트셀러
        top_selling = sales.values('card_version__card__name_kr').annotate(
            quantity_sold=Sum(F('quantity_change') * -1),
            revenue=Sum('total_amount')
        ).order_by('-quantity_sold')[:10]
        
        stats['top_selling_cards'] = list(top_selling)
        stats['period'] = period
        
        return Response(stats)
    


class GameSetsView(ListAPIView):
    """특정 게임의 카드 세트 목록"""
    serializer_class = CardSetSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        game_slug = self.kwargs['slug']
        return CardSet.objects.filter(
            game__slug=game_slug, 
            is_active=True
        ).order_by('-release_date')


class SetCardsView(ListAPIView):
    """특정 세트의 카드 목록"""
    serializer_class = CardSimpleSerializer
    permission_classes = [AllowAny]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'name_kr', 'card_number']
    ordering_fields = ['card_number', 'name']
    ordering = ['card_number']
    
    def get_queryset(self):
        set_code = self.kwargs['set_code']
        return Card.objects.filter(
            set__set_code=set_code
        ).select_related('game', 'set')


# TCGGameViewSet에 추가 action
# 기존 TCGGameViewSet 클래스에 다음 메서드 추가:

@action(detail=True, methods=['get'])
def sets(self, request, slug=None):
    """특정 게임의 카드 세트 목록"""
    game = self.get_object()
    sets = game.sets.filter(is_active=True).order_by('-release_date')
    serializer = CardSetSerializer(sets, many=True)
    return Response(serializer.data)

@action(detail=True, methods=['get']) 
def statistics(self, request, slug=None):
    """게임별 통계"""
    game = self.get_object()
    stats = {
        'total_sets': game.sets.count(),
        'total_cards': game.cards.count(),
        'latest_set': None
    }
    
    latest_set = game.sets.filter(is_active=True).order_by('-release_date').first()
    if latest_set:
        stats['latest_set'] = {
            'name': latest_set.name_kr or latest_set.name,
            'set_code': latest_set.set_code,
            'release_date': latest_set.release_date
        }
    
    return Response(stats)