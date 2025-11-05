# my_app/management/commands/clear_digimon_set.py

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from cardStockManageApp.models import TCGGame, CardSet, Card, CardVersion


class Command(BaseCommand):
    help = '디지몬 특정 세트의 카드 데이터를 삭제합니다'

    def add_arguments(self, parser):
        parser.add_argument(
            '--set-code',
            type=str,
            help='삭제할 세트 코드 (예: BT16, EX07, ST18)'
        )
        parser.add_argument(
            '--set-name',
            type=str,
            help='삭제할 세트 이름 (예: BTK-17, EXK-06)'
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
            help='현재 등록된 디지몬 세트 목록 출력'
        )
        parser.add_argument(
            '--keep-set',
            action='store_true',
            help='세트 정보는 유지하고 카드만 삭제'
        )
        parser.add_argument(
            '--exact',
            action='store_true',
            help='입력한 세트 코드를 정확히 그대로 사용 (자동 변환 안함)'
        )

    def handle(self, *args, **options):
        self.set_code = options.get('set_code')
        self.set_name = options.get('set_name')
        self.confirm = options['confirm']
        self.dry_run = options['dry_run']
        self.list_sets = options['list_sets']
        self.keep_set = options['keep_set']
        self.exact = options['exact']
        
        # 디지몬 게임 확인
        try:
            self.digimon_game = TCGGame.objects.get(name='Digimon')
        except TCGGame.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('디지몬 게임이 등록되지 않았습니다.')
            )
            return
        
        if self.list_sets:
            self.show_digimon_sets()
            return
        
        if not self.set_code and not self.set_name:
            self.stdout.write(
                self.style.ERROR('--set-code 또는 --set-name 중 하나를 지정해주세요.')
            )
            self.stdout.write('현재 세트 목록: python manage.py clear_digimon_set --list-sets')
            return
        
        if self.dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN 모드: 실제 삭제하지 않습니다')
            )
        
        try:
            self.delete_digimon_set()
        except Exception as e:
            raise CommandError(f'삭제 중 오류 발생: {e}')

    def normalize_set_code(self, input_code):
        """
        입력된 세트 코드를 정규화
        BT16 -> BTK-16, BTK-16 -> BTK-16
        """
        import re
        
        # 이미 BTK-16 형식인 경우
        if re.match(r'[A-Z]+K-\d+', input_code):
            return input_code
        
        # BT16 형식인 경우 BTK-16으로 변환
        match = re.match(r'([A-Z]+)(\d+)', input_code)
        if match:
            prefix = match.group(1)
            number = match.group(2)
            return f"{prefix}K-{number}"
        
        return input_code

    def show_digimon_sets(self):
        """현재 등록된 디지몬 세트 목록 출력"""
        
        sets = CardSet.objects.filter(game=self.digimon_game).order_by('set_code')
        
        if not sets.exists():
            self.stdout.write(
                self.style.WARNING('등록된 디지몬 세트가 없습니다.')
            )
            return
        
        self.stdout.write(self.style.SUCCESS('현재 등록된 디지몬 세트 목록\n'))
        
        for card_set in sets:
            cards_count = Card.objects.filter(set=card_set).count()
            versions_count = CardVersion.objects.filter(card__set=card_set).count()
            
            self.stdout.write(
                f"[{card_set.set_code}] {card_set.name_kr}"
            )
            self.stdout.write(
                f"   카드: {cards_count}장, 버전: {versions_count}개"
            )
            self.stdout.write("")
        
        self.stdout.write(f"총 {sets.count()}개 세트")
        
        # 사용법 안내
        self.stdout.write(self.style.SUCCESS('\n사용법:'))
        self.stdout.write('   # 일반 삭제 (BT16 입력 시 BTK-16으로 자동 변환)')
        self.stdout.write('   python manage.py clear_digimon_set --set-code BT16')
        self.stdout.write('')
        self.stdout.write('   # 레거시 BT16 형식 삭제 (자동 변환 없이 정확히 BT16만 삭제)')
        self.stdout.write('   python manage.py clear_digimon_set --set-code BT16 --exact')
        self.stdout.write('')
        self.stdout.write('   # 세트 정보는 유지하고 카드만 삭제')
        self.stdout.write('   python manage.py clear_digimon_set --set-code BT16 --keep-set')

    def delete_digimon_set(self):
        """디지몬 세트 삭제"""
        
        # 입력된 세트 코드 처리
        if self.set_code:
            input_code = self.set_code
        elif self.set_name:
            input_code = self.set_name
        else:
            return
        
        # --exact 옵션이 있으면 입력 그대로 사용
        if self.exact:
            target_set_code = input_code
        else:
            # 정규화 (BT16 -> BTK-16)
            target_set_code = self.normalize_set_code(input_code)
        
        # 세트 존재 확인
        card_set = None
        
        # 먼저 입력된 형식 그대로 찾기
        try:
            card_set = CardSet.objects.get(
                game=self.digimon_game,
                set_code=target_set_code
            )
        except CardSet.DoesNotExist:
            # exact 모드가 아니면 다른 형식도 시도
            if not self.exact:
                import re
                match = re.match(r'([A-Z]+)K-(\d+)', target_set_code)
                if match:
                    # BTK-16 -> BT16 시도
                    prefix = match.group(1)
                    number = match.group(2)
                    legacy_code = f"{prefix}{number}"
                    
                    try:
                        card_set = CardSet.objects.get(
                            game=self.digimon_game,
                            set_code=legacy_code
                        )
                    except CardSet.DoesNotExist:
                        pass
        
        if not card_set:
            self.stdout.write(
                self.style.ERROR(f'세트를 찾을 수 없습니다: {target_set_code}')
            )
            self.stdout.write('현재 세트 목록: python manage.py clear_digimon_set --list-sets')
            self.stdout.write('\nTIP: 정확한 세트 코드로 삭제하려면 --exact 옵션을 사용하세요')
            self.stdout.write('예: python manage.py clear_digimon_set --set-code BT16 --exact')
            return
        
        # 삭제 대상 카운트
        cards = Card.objects.filter(set=card_set)
        versions = CardVersion.objects.filter(card__set=card_set)
        
        cards_count = cards.count()
        versions_count = versions.count()
        
        # 삭제 정보 출력
        self.stdout.write(f'삭제 대상 세트: [{card_set.set_code}] {card_set.name_kr}')
        self.stdout.write(f'   카드: {cards_count}장')
        self.stdout.write(f'   버전: {versions_count}개')
        
        if cards_count == 0:
            self.stdout.write(
                self.style.WARNING('삭제할 카드가 없습니다.')
            )
            
            # 빈 세트 삭제 여부 확인
            if not self.dry_run and not self.keep_set:
                if self.confirm or self._confirm_action('빈 세트도 삭제하시겠습니까?'):
                    card_set.delete()
                    self.stdout.write(
                        self.style.SUCCESS('빈 세트가 삭제되었습니다.')
                    )
            return
        
        if self.dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN: 실제로는 삭제되지 않습니다.')
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
            self.stdout.write('삭제 진행 중...')
            
            # CardVersion 삭제 (관련 데이터도 연쇄 삭제됨)
            if versions_count > 0:
                versions.delete()
                self.stdout.write(f'   {versions_count}개 카드 버전 삭제')
            
            # Card 삭제
            if cards_count > 0:
                cards.delete()
                self.stdout.write(f'   {cards_count}장 카드 삭제')
            
            # 세트 삭제 여부 확인
            if not self.keep_set:
                if self.confirm or self._confirm_action('세트 정보도 삭제하시겠습니까?'):
                    card_set.delete()
                    self.stdout.write(f'   세트 [{card_set.set_code}] 삭제')
                else:
                    self.stdout.write(f'   세트 [{card_set.set_code}] 유지 (카드만 삭제)')
            else:
                self.stdout.write(f'   세트 [{card_set.set_code}] 유지 (카드만 삭제)')
        
        # 완료 메시지
        self.stdout.write(
            self.style.SUCCESS(f'\n삭제 완료!')
        )
        self.stdout.write(f'삭제된 카드: {cards_count}장')
        self.stdout.write(f'삭제된 버전: {versions_count}개')

    def _confirm_action(self, message):
        """사용자 확인"""
        self.stdout.write(
            self.style.WARNING(f'\n{message}')
        )
        response = input('계속하시겠습니까? (yes/no): ')
        return response.lower() in ['yes', 'y']