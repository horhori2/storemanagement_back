# my_app/management/commands/clear_onepiece_set.py

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from cardStockManageApp.models import TCGGame, CardSet, Card, CardVersion


class Command(BaseCommand):
    help = '원피스 특정 세트의 카드 데이터를 삭제합니다'

    def add_arguments(self, parser):
        parser.add_argument(
            '--set-code',
            type=str,
            help='삭제할 세트 코드 (예: OP07, ST14)'
        )
        parser.add_argument(
            '--series-code',
            type=str,
            help='삭제할 시리즈 코드 (예: OPK-07, STK-14)'
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='확인 없이 바로 삭제'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='실제 삭제하지 않고 확인만'
        )
        parser.add_argument(
            '--list-sets',
            action='store_true',
            help='현재 등록된 원피스 세트 목록 출력'
        )

    def handle(self, *args, **options):
        self.set_code = options.get('set_code')
        self.series_code = options.get('series_code')
        self.confirm = options['confirm']
        self.dry_run = options['dry_run']
        self.list_sets = options['list_sets']
        
        # 원피스 게임 확인
        try:
            self.onepiece_game = TCGGame.objects.get(name='OnePiece')
        except TCGGame.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('❌ 원피스 게임이 등록되지 않았습니다.')
            )
            return
        
        if self.list_sets:
            self.show_onepiece_sets()
            return
        
        if not self.set_code and not self.series_code:
            self.stdout.write(
                self.style.ERROR('❌ --set-code 또는 --series-code 중 하나를 지정해주세요.')
            )
            self.stdout.write('💡 현재 세트 목록: python manage.py clear_onepiece_set --list-sets')
            return
        
        if self.dry_run:
            self.stdout.write(
                self.style.WARNING('🧪 DRY RUN 모드: 실제 삭제하지 않습니다')
            )
        
        try:
            self.delete_onepiece_set()
        except Exception as e:
            raise CommandError(f'삭제 중 오류 발생: {e}')

    def get_series_mapping(self):
        """시리즈 코드 -> 세트 코드 매핑"""
        return {
            'OPK-07': 'OP07',
            'EBK-01': 'EB01',
            'OPK-06': 'OP06',
            'OPK-05': 'OP05',
            'OPK-04': 'OP04',
            'OPK-03': 'OP03',
            'OPK-02': 'OP02',
            'OPK-01': 'OP01',
            'STK-14': 'ST14',
            'STK-13': 'ST13',
            'STK-12': 'ST12',
            'STK-11': 'ST11',
            'STK-10': 'ST10',
            'STK-09': 'ST09',
            'STK-08': 'ST08',
            'STK-07': 'ST07',
            'STK-06': 'ST06',
            'STK-05': 'ST05',
            'STK-04': 'ST04',
            'STK-03': 'ST03',
            'STK-02': 'ST02',
            'STK-01': 'ST01',
        }

    def show_onepiece_sets(self):
        """현재 등록된 원피스 세트 목록 출력"""
        
        sets = CardSet.objects.filter(game=self.onepiece_game).order_by('set_code')
        
        if not sets.exists():
            self.stdout.write(
                self.style.WARNING('📋 등록된 원피스 세트가 없습니다.')
            )
            return
        
        self.stdout.write(self.style.SUCCESS('📋 현재 등록된 원피스 세트 목록\n'))
        
        # 시리즈 매핑 역으로 변환
        series_mapping = self.get_series_mapping()
        reverse_mapping = {v: k for k, v in series_mapping.items()}
        
        for card_set in sets:
            cards_count = Card.objects.filter(set=card_set).count()
            versions_count = CardVersion.objects.filter(card__set=card_set).count()
            
            # 시리즈 코드 찾기
            series_code = reverse_mapping.get(card_set.set_code, '알 수 없음')
            
            self.stdout.write(
                f"📦 [{card_set.set_code}] {card_set.name_kr}"
            )
            self.stdout.write(
                f"   🌐 시리즈 코드: {series_code}"
            )
            self.stdout.write(
                f"   🃏 카드: {cards_count}장, 버전: {versions_count}개"
            )
            self.stdout.write("")
        
        self.stdout.write(f"📊 총 {sets.count()}개 세트")
        
        # 사용법 안내
        self.stdout.write(self.style.SUCCESS('\n💡 사용법:'))
        self.stdout.write('   # 세트 코드로 삭제')
        self.stdout.write('   python manage.py clear_onepiece_set --set-code OP07')
        self.stdout.write('')
        self.stdout.write('   # 시리즈 코드로 삭제')
        self.stdout.write('   python manage.py clear_onepiece_set --series-code OPK-07')

    def delete_onepiece_set(self):
        """원피스 세트 삭제"""
        
        # 대상 세트 찾기
        target_set_code = self.set_code
        
        if self.series_code:
            # 시리즈 코드를 세트 코드로 변환
            series_mapping = self.get_series_mapping()
            target_set_code = series_mapping.get(self.series_code)
            
            if not target_set_code:
                self.stdout.write(
                    self.style.ERROR(f'❌ 알 수 없는 시리즈 코드: {self.series_code}')
                )
                self.stdout.write('💡 지원되는 시리즈 코드: ' + ', '.join(series_mapping.keys()))
                return
        
        # 세트 존재 확인
        try:
            card_set = CardSet.objects.get(
                game=self.onepiece_game,
                set_code=target_set_code
            )
        except CardSet.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'❌ 세트를 찾을 수 없습니다: {target_set_code}')
            )
            self.stdout.write('💡 현재 세트 목록: python manage.py clear_onepiece_set --list-sets')
            return
        
        # 삭제 대상 카운트
        cards = Card.objects.filter(set=card_set)
        versions = CardVersion.objects.filter(card__set=card_set)
        
        cards_count = cards.count()
        versions_count = versions.count()
        
        # 삭제 정보 출력
        self.stdout.write(f'🗑️ 삭제 대상 세트: [{card_set.set_code}] {card_set.name_kr}')
        self.stdout.write(f'   🃏 카드: {cards_count}장')
        self.stdout.write(f'   🎨 버전: {versions_count}개')
        
        if cards_count == 0:
            self.stdout.write(
                self.style.WARNING('⚠️ 삭제할 카드가 없습니다.')
            )
            
            # 빈 세트 삭제 여부 확인
            if not self.dry_run:
                if self.confirm or self._confirm_action('빈 세트도 삭제하시겠습니까?'):
                    card_set.delete()
                    self.stdout.write(
                        self.style.SUCCESS('✅ 빈 세트가 삭제되었습니다.')
                    )
            return
        
        if self.dry_run:
            self.stdout.write(
                self.style.WARNING('🧪 DRY RUN: 실제로는 삭제되지 않습니다.')
            )
            return
        
        # 삭제 확인
        if not self.confirm:
            if not self._confirm_action('정말로 삭제하시겠습니까?'):
                self.stdout.write('취소되었습니다.')
                return
        
        # 실제 삭제 수행
        with transaction.atomic():
            
            # 상세 삭제 로그
            self.stdout.write('🔄 삭제 진행 중...')
            
            # CardVersion 삭제 (관련 데이터도 연쇄 삭제됨)
            if versions_count > 0:
                versions.delete()
                self.stdout.write(f'   ✅ {versions_count}개 카드 버전 삭제')
            
            # Card 삭제
            if cards_count > 0:
                cards.delete()
                self.stdout.write(f'   ✅ {cards_count}장 카드 삭제')
            
            # 세트 삭제 여부 확인
            if self.confirm or self._confirm_action('세트 정보도 삭제하시겠습니까?'):
                card_set.delete()
                self.stdout.write(f'   ✅ 세트 [{card_set.set_code}] 삭제')
            else:
                self.stdout.write(f'   📋 세트 [{card_set.set_code}] 유지 (카드만 삭제)')
        
        # 완료 메시지
        self.stdout.write(
            self.style.SUCCESS(f'\n🎉 삭제 완료!')
        )
        self.stdout.write(f'📊 삭제된 카드: {cards_count}장')
        self.stdout.write(f'📊 삭제된 버전: {versions_count}개')

    def _confirm_action(self, message):
        """사용자 확인"""
        self.stdout.write(
            self.style.WARNING(f'\n⚠️ {message}')
        )
        response = input('계속하시겠습니까? (yes/no): ')
        return response.lower() in ['yes', 'y']

    def get_set_info_by_code(self, set_code):
        """세트 코드로 상세 정보 반환"""
        try:
            card_set = CardSet.objects.get(
                game=self.onepiece_game,
                set_code=set_code
            )
            
            cards_count = Card.objects.filter(set=card_set).count()
            versions_count = CardVersion.objects.filter(card__set=card_set).count()
            
            return {
                'set': card_set,
                'cards_count': cards_count,
                'versions_count': versions_count
            }
        except CardSet.DoesNotExist:
            return None