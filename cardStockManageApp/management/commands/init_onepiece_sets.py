# my_app/management/commands/init_onepiece_sets.py

from django.core.management.base import BaseCommand
from django.db import transaction

from cardStockManageApp.models import TCGGame, CardSet, Rarity


class Command(BaseCommand):
    help = '모든 원피스 카드 세트 정보를 DB에 초기화합니다'

    def add_arguments(self, parser):
        parser.add_argument(
            '--update',
            action='store_true',
            help='기존 세트 정보도 업데이트'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='실제 저장하지 않고 확인만'
        )

    def handle(self, *args, **options):
        self.update_existing = options['update']
        self.dry_run = options['dry_run']
        
        if self.dry_run:
            self.stdout.write(
                self.style.WARNING('🧪 DRY RUN 모드: 실제 저장하지 않습니다')
            )
        
        self.stdout.write(
            self.style.SUCCESS('🎯 원피스 카드 세트 초기화 시작...')
        )
        
        try:
            self.init_all_onepiece_sets()
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ 오류 발생: {e}')
            )

    def get_all_onepiece_sets(self):
        """모든 원피스 세트 정보"""
        return {
            'OPK-07': ('OP07', '부스터 팩 500년 후의 미래', '500년 후의 미래'),
            'EBK-01': ('EB01', '엑스트라 부스터 팩 메모리얼 컬렉션', '메모리얼 컬렉션'),
            'OPK-06': ('OP06', '부스터 팩 쌍벽의 패자', '쌍벽의 패자'),
            'OPK-05': ('OP05', '부스터 팩 신시대의 주역', '신시대의 주역'),
            'OPK-04': ('OP04', '부스터 팩 모략의 왕국', '모략의 왕국'),
            'OPK-03': ('OP03', '부스터 팩 강대한 적', '강대한 적'),
            'OPK-02': ('OP02', '부스터 팩 정상결전', '정상결전'),
            'OPK-01': ('OP01', '부스터 팩 ROMANCE DAWN', 'ROMANCE DAWN'),
            'STK-14': ('ST14', '스타트 덱 3D2Y', '3D2Y'),
            'STK-13': ('ST13', '스타트 덱 울트라덱 세 형제의 인연', '세 형제의 인연'),
            'STK-12': ('ST12', '스타트 덱 조로&사우전드 써니', '조로&사우전드 써니'),
            'STK-11': ('ST11', '스타트 덱 우타', '우타'),
            'STK-10': ('ST10', '스타트 덱 빅 맘 해적단', '빅 맘 해적단'),
            'STK-09': ('ST09', '스타트 덱 야마토', '야마토'),
            'STK-08': ('ST08', '스타트 덱 몽키 D. 루피', '몽키 D. 루피'),
            'STK-07': ('ST07', '스타트 덱 빅 맘 해적단', '빅 맘 해적단'),
            'STK-06': ('ST06', '스타트 덱 절대정의', '절대정의'),
            'STK-05': ('ST05', '스타트 덱 원피스 필름 에디션', '원피스 필름 에디션'),
            'STK-04': ('ST04', '스타트 덱 애니멀 킹덤 해적단', '애니멀 킹덤 해적단'),
            'STK-03': ('ST03', '스타트 덱 검은 수염 해적단', '검은 수염 해적단'),
            'STK-02': ('ST02', '스타트 덱 최악의 세대', '최악의 세대'),
            'STK-01': ('ST01', '스타트 덱 밀짚모자 일당', '밀짚모자 일당'),
        }

    def init_all_onepiece_sets(self):
        """모든 원피스 세트 초기화"""
        
        if not self.dry_run:
            # 원피스 게임 생성
            onepiece_game, game_created = TCGGame.objects.get_or_create(
                name='OnePiece',
                defaults={
                    'name_kr': '원피스',
                    'slug': 'onepiece',
                    'is_active': True
                }
            )
            
            if game_created:
                self.stdout.write(f"✅ TCG 게임 생성: {onepiece_game}")
            else:
                self.stdout.write(f"📋 기존 게임 사용: {onepiece_game}")
            
            # 원피스 레어도 생성
            self.create_onepiece_rarities(onepiece_game)
        else:
            try:
                onepiece_game = TCGGame.objects.get(name='OnePiece')
                self.stdout.write(f"📋 대상 게임: {onepiece_game}")
            except TCGGame.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR('❌ 원피스 게임이 없습니다. --dry-run 없이 실행해주세요.')
                )
                return

        # 모든 세트 처리
        all_sets = self.get_all_onepiece_sets()
        
        created_count = 0
        updated_count = 0
        skipped_count = 0
        
        self.stdout.write(f"\n📦 총 {len(all_sets)}개 세트 처리 중...")
        
        for series_code, (set_code, set_name, set_name_kr) in all_sets.items():
            
            if self.dry_run:
                # Dry run 모드
                try:
                    existing_set = CardSet.objects.get(game=onepiece_game, set_code=set_code)
                    self.stdout.write(
                        f"📋 기존: [{set_code}] {set_name_kr} (시리즈: {series_code})"
                    )
                    skipped_count += 1
                except CardSet.DoesNotExist:
                    self.stdout.write(
                        f"🆕 신규: [{set_code}] {set_name_kr} (시리즈: {series_code})"
                    )
                    created_count += 1
                continue
            
            # 실제 저장
            with transaction.atomic():
                card_set, created = CardSet.objects.get_or_create(
                    game=onepiece_game,
                    set_code=set_code,
                    defaults={
                        'name': set_name,
                        'name_kr': set_name_kr,
                        'is_active': True
                    }
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f"✅ 세트 생성: [{set_code}] {set_name_kr}")
                    )
                else:
                    # 기존 세트 업데이트 (옵션이 켜져있을 때만)
                    if self.update_existing:
                        updated = False
                        if card_set.name != set_name:
                            card_set.name = set_name
                            updated = True
                        if card_set.name_kr != set_name_kr:
                            card_set.name_kr = set_name_kr
                            updated = True
                        
                        if updated:
                            card_set.save()
                            updated_count += 1
                            self.stdout.write(
                                f"📝 세트 업데이트: [{set_code}] {set_name_kr}"
                            )
                        else:
                            skipped_count += 1
                            self.stdout.write(
                                f"⏭️ 변경없음: [{set_code}] {set_name_kr}"
                            )
                    else:
                        skipped_count += 1
                        self.stdout.write(
                            f"⏭️ 기존: [{set_code}] {set_name_kr}"
                        )
        
        # 결과 출력
        self.stdout.write(self.style.SUCCESS(f"\n🎉 원피스 세트 초기화 완료!"))
        if self.dry_run:
            self.stdout.write(f"📊 신규 예정: {created_count}개")
            self.stdout.write(f"📊 기존: {skipped_count}개")
        else:
            self.stdout.write(f"📊 신규 생성: {created_count}개")
            self.stdout.write(f"📊 업데이트: {updated_count}개")
            self.stdout.write(f"📊 기존 유지: {skipped_count}개")
            self.stdout.write(f"📊 총 세트: {CardSet.objects.filter(game=onepiece_game).count()}개")

    def create_onepiece_rarities(self, game):
        """원피스 레어도 생성"""
        onepiece_rarities = [
            ('C', 'Common', '커먼'),
            ('UC', 'Uncommon', '언커먼'),
            ('R', 'Rare', '레어'),
            ('SR', 'Super Rare', '슈퍼레어'),
            ('SEC', 'Secret', '시크릿'),
            ('L', 'Leader', '리더'),
            ('P-C', 'Promo Common', '프로모 커먼'),
            ('P-UC', 'Promo Uncommon', '프로모 언커먼'),
            ('P-R', 'Promo Rare', '프로모 레어'),
            ('P-SR', 'Promo Super Rare', '프로모 슈퍼레어'),
            ('P-SEC', 'Promo Secret', '프로모 시크릿'),
            ('P-L', 'Promo Leader', '프로모 리더'),
            ('SP-C', 'Special Common', '스페셜 커먼'),
            ('SP-UC', 'Special Uncommon', '스페셜 언커먼'),
            ('SP-R', 'Special Rare', '스페셜 레어'),
            ('SP-SR', 'Special Super Rare', '스페셜 슈퍼레어'),
            ('SP-SEC', 'Special Secret', '스페셜 시크릿'),
            ('SP-L', 'Special Leader', '스페셜 리더'),
        ]
        
        created_rarities = 0
        for rarity_code, rarity_name, rarity_name_kr in onepiece_rarities:
            rarity, created = Rarity.objects.get_or_create(
                game=game,
                rarity_code=rarity_code,
                defaults={
                    'rarity_name': rarity_name,
                    'rarity_name_kr': rarity_name_kr,
                }
            )
            if created:
                created_rarities += 1
                self.stdout.write(f"✅ 레어도 생성: {rarity}")
        
        if created_rarities > 0:
            self.stdout.write(f"📊 레어도 {created_rarities}개 생성됨")