# my_app/management/commands/clear_card_data.py

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from cardStockManageApp.models import (
    TCGGame, CardSet, Rarity, Card, CardVersion, 
    Inventory, Price, InventoryLog, PriceHistory, 
    DailyPriceHistory, CardVersionAlias, MarketPrice
)


class Command(BaseCommand):
    help = '카드 관련 데이터를 선택적으로 초기화합니다'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='모든 카드 관련 데이터 삭제'
        )
        parser.add_argument(
            '--cards-only',
            action='store_true',
            help='카드와 카드버전만 삭제 (게임, 세트, 레어도는 유지)'
        )
        parser.add_argument(
            '--set-code',
            type=str,
            help='특정 세트의 카드만 삭제'
        )
        parser.add_argument(
            '--game',
            type=str,
            default='Pokemon',
            help='대상 게임 (기본값: Pokemon)'
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='확인 없이 바로 삭제'
        )

    def handle(self, *args, **options):
        self.game_name = options['game']
        self.set_code = options.get('set_code')
        self.confirm = options['confirm']

        # sell_price가 None인 경우 0으로 설정
        Price.objects.filter(sell_price__isnull=True).update(sell_price=0)
        Price.objects.filter(buy_price__isnull=True).update(buy_price=0)
        
        try:
            game = TCGGame.objects.get(name=self.game_name)
        except TCGGame.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'게임을 찾을 수 없습니다: {self.game_name}')
            )
            return

        if options['all']:
            self.clear_all_data(game)
        elif options['cards_only']:
            self.clear_cards_only(game)
        elif self.set_code:
            self.clear_set_data(game, self.set_code)
        else:
            self.stdout.write(
                self.style.ERROR('옵션을 선택해주세요: --all, --cards-only, 또는 --set-code')
            )

    def confirm_deletion(self, message):
        """삭제 확인"""
        if self.confirm:
            return True
        
        self.stdout.write(self.style.WARNING(f'\n⚠️  {message}'))
        response = input('계속하시겠습니까? (yes/no): ')
        return response.lower() in ['yes', 'y']

    def clear_all_data(self, game):
        """모든 카드 관련 데이터 삭제"""
        
        if not self.confirm_deletion(
            f'{game.name} 게임의 모든 데이터가 삭제됩니다.'
        ):
            self.stdout.write('취소되었습니다.')
            return

        with transaction.atomic():
            # 관련 데이터 카운트
            cards_count = Card.objects.filter(game=game).count()
            versions_count = CardVersion.objects.filter(card__game=game).count()
            sets_count = CardSet.objects.filter(game=game).count()
            rarities_count = Rarity.objects.filter(game=game).count()

            self.stdout.write(f'🗑️  삭제 대상:')
            self.stdout.write(f'   - 카드: {cards_count}개')
            self.stdout.write(f'   - 카드 버전: {versions_count}개')
            self.stdout.write(f'   - 세트: {sets_count}개')
            self.stdout.write(f'   - 레어도: {rarities_count}개')

            # 연쇄 삭제 (외래키 관계로 자동 삭제됨)
            Card.objects.filter(game=game).delete()
            CardSet.objects.filter(game=game).delete()
            Rarity.objects.filter(game=game).delete()
            
            # 게임도 삭제할지 선택
            if self.confirm_deletion('게임 정보도 삭제하시겠습니까?'):
                game.delete()
                self.stdout.write(
                    self.style.SUCCESS(f'✅ {self.game_name} 게임이 완전히 삭제되었습니다.')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ {self.game_name} 게임의 모든 카드 데이터가 삭제되었습니다.')
                )

    def clear_cards_only(self, game):
        """카드와 카드버전만 삭제 (게임, 세트, 레어도는 유지)"""
        
        if not self.confirm_deletion(
            f'{game.name} 게임의 모든 카드와 카드버전이 삭제됩니다. (세트, 레어도는 유지)'
        ):
            self.stdout.write('취소되었습니다.')
            return

        with transaction.atomic():
            cards_count = Card.objects.filter(game=game).count()
            versions_count = CardVersion.objects.filter(card__game=game).count()

            self.stdout.write(f'🗑️  삭제 대상:')
            self.stdout.write(f'   - 카드: {cards_count}개')
            self.stdout.write(f'   - 카드 버전: {versions_count}개')

            # 카드만 삭제 (CardVersion은 외래키로 연쇄 삭제)
            Card.objects.filter(game=game).delete()

            self.stdout.write(
                self.style.SUCCESS(f'✅ {cards_count}개 카드와 {versions_count}개 카드버전이 삭제되었습니다.')
            )

    def clear_set_data(self, game, set_code):
        """특정 세트의 카드만 삭제"""
        
        try:
            card_set = CardSet.objects.get(game=game, set_code=set_code)
        except CardSet.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'세트를 찾을 수 없습니다: {set_code}')
            )
            return

        if not self.confirm_deletion(
            f'{card_set.name} ({set_code}) 세트의 모든 카드가 삭제됩니다.'
        ):
            self.stdout.write('취소되었습니다.')
            return

        with transaction.atomic():
            cards_count = Card.objects.filter(set=card_set).count()
            versions_count = CardVersion.objects.filter(card__set=card_set).count()

            self.stdout.write(f'🗑️  삭제 대상:')
            self.stdout.write(f'   - 세트: {card_set.name}')
            self.stdout.write(f'   - 카드: {cards_count}개')
            self.stdout.write(f'   - 카드 버전: {versions_count}개')

            # 해당 세트의 카드만 삭제
            Card.objects.filter(set=card_set).delete()

            self.stdout.write(
                self.style.SUCCESS(f'✅ {set_code} 세트의 {cards_count}개 카드가 삭제되었습니다.')
            )

    def get_data_summary(self, game):
        """현재 데이터 현황 출력"""
        cards = Card.objects.filter(game=game)
        versions = CardVersion.objects.filter(card__game=game)
        sets = CardSet.objects.filter(game=game)
        
        self.stdout.write(f'\n📊 {game.name} 현재 데이터:')
        self.stdout.write(f'   - 세트: {sets.count()}개')
        self.stdout.write(f'   - 카드: {cards.count()}개')
        self.stdout.write(f'   - 카드 버전: {versions.count()}개')
        
        # 세트별 상세
        for card_set in sets:
            set_cards = cards.filter(set=card_set).count()
            self.stdout.write(f'     └ {card_set.set_code}: {set_cards}장')