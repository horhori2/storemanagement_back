# my_app/management/commands/crawl_cards_onepiece.py

# # ✅ 특정 시리즈 크롤링
# python manage.py crawl_onepiece_cards --series-code OPK-07

# # ✅ 모든 시리즈 크롤링
# python manage.py crawl_onepiece_cards --all-series

# # 🧪 테스트 모드
# python manage.py crawl_onepiece_cards --series-code STK-14 --dry-run

# # ⏱️ 페이지 간 대기시간 조정 (서버 부하 방지)
# python manage.py crawl_onepiece_cards --series-code OPK-06 --delay 2.0

# # 🔥 모든 시리즈를 빠르게 크롤링
# python manage.py crawl_onepiece_cards --all-series --delay 0.5

# # 🧪 모든 시리즈 테스트
# python manage.py crawl_onepiece_cards --all-series --dry-run

# my_app/management/commands/crawl_onepiece_cards.py

# my_app/management/commands/crawl_onepiece_cards.py

import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
import re
import time

from cardStockManageApp.models import TCGGame, CardSet, Rarity, Card, CardVersion


class Command(BaseCommand):
    help = '원피스 카드 정보를 크롤링하여 DB에 저장합니다'

    def add_arguments(self, parser):
        parser.add_argument(
            '--series-code',
            type=str,
            default='OPK-07',
            help='크롤링할 시리즈 코드 (기본값: OPK-07)'
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=1.0,
            help='페이지 간 대기 시간(초) (기본값: 1.0)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='실제 저장하지 않고 크롤링만 테스트'
        )
        parser.add_argument(
            '--all-series',
            action='store_true',
            help='모든 시리즈 크롤링'
        )

    def handle(self, *args, **options):
        self.series_code = options['series_code']
        self.delay = options['delay']
        self.dry_run = options['dry_run']
        self.all_series = options['all_series']
        
        if self.dry_run:
            self.stdout.write(
                self.style.WARNING('🧪 DRY RUN 모드: 실제 저장하지 않습니다')
            )
        
        if self.all_series:
            self.stdout.write(
                self.style.SUCCESS('🎯 모든 원피스 시리즈 크롤링 시작!')
            )
            self.crawl_all_onepiece_series()
        else:
            series_info = self.get_series_info(self.series_code)
            if not series_info:
                self.stdout.write(
                    self.style.ERROR(f'❌ 지원하지 않는 시리즈 코드입니다: {self.series_code}')
                )
                return
            
            self.stdout.write(
                self.style.SUCCESS(f'🎯 원피스 시리즈 크롤링 시작: {series_info["name_kr"]}')
            )
            self.crawl_single_series()

    def get_all_series_mapping(self):
        """모든 원피스 시리즈 매핑 - 딕셔너리 형태로 반환"""
        return {
            'OPK-08': {
                'set_code': 'OPK-08',
                'display_code': 'OP08',
                'name': '두 전설',
                'name_kr': '부스터 팩 두 전설'
            },
            'OPK-07': {
                'set_code': 'OPK-07',
                'display_code': 'OP07',
                'name': '500년 후의 미래',
                'name_kr': '부스터 팩 500년 후의 미래'
            },
            'EBK-01': {
                'set_code': 'EBK-01',
                'display_code': 'EB01',
                'name': '메모리얼 컬렉션',
                'name_kr': '엑스트라 부스터 팩 메모리얼 컬렉션'
            },
            'OPK-06': {
                'set_code': 'OPK-06',
                'display_code': 'OP06',
                'name': '쌍벽의 패자',
                'name_kr': '부스터 팩 쌍벽의 패자'
            },
            'OPK-05': {
                'set_code': 'OPK-05',
                'display_code': 'OP05',
                'name': '신시대의 주역',
                'name_kr': '부스터 팩 신시대의 주역'
            },
            'OPK-04': {
                'set_code': 'OPK-04',
                'display_code': 'OP04',
                'name': '모략의 왕국',
                'name_kr': '부스터 팩 모략의 왕국'
            },
            'OPK-03': {
                'set_code': 'OPK-03',
                'display_code': 'OP03',
                'name': '강대한 적',
                'name_kr': '부스터 팩 강대한 적'
            },
            'OPK-02': {
                'set_code': 'OPK-02',
                'display_code': 'OP02',
                'name': '정상결전',
                'name_kr': '부스터 팩 정상결전'
            },
            'OPK-01': {
                'set_code': 'OPK-01',
                'display_code': 'OP01',
                'name': 'ROMANCE DAWN',
                'name_kr': '부스터 팩 ROMANCE DAWN'
            },
            'STK-14': {
                'set_code': 'STK-14',
                'display_code': 'ST14',
                'name': '3D2Y',
                'name_kr': '스타트 덱 3D2Y'
            },
            'STK-13': {
                'set_code': 'STK-13',
                'display_code': 'ST13',
                'name': '3형제의 유대',
                'name_kr': '스타트 덱 3형제의 유대'
            },
            'STK-12': {
                'set_code': 'STK-12',
                'display_code': 'ST12',
                'name': '조로 & 상디',
                'name_kr': '스타트 덱 조로 & 상디'
            },
            'STK-11': {
                'set_code': 'STK-11',
                'display_code': 'ST11',
                'name': 'Side 우타',
                'name_kr': '스타트 덱 Side 우타'
            },
            'STK-10': {
                'set_code': 'STK-10',
                'display_code': 'ST10',
                'name': '"삼선장" 집결',
                'name_kr': '얼티밋 덱 "삼선장" 집결'
            },
            'STK-09': {
                'set_code': 'STK-09',
                'display_code': 'ST09',
                'name': 'Side 야마토',
                'name_kr': '스타트 덱 Side 야마토'
            },
            'STK-08': {
                'set_code': 'STK-08',
                'display_code': 'ST08',
                'name': 'Side 몽키 D. 루피',
                'name_kr': '스타트 덱 Side 몽키 D. 루피'
            },
            'STK-07': {
                'set_code': 'STK-07',
                'display_code': 'ST07',
                'name': '빅 맘 해적단',
                'name_kr': '스타트 덱 빅 맘 해적단'
            },
            'STK-06': {
                'set_code': 'STK-06',
                'display_code': 'ST06',
                'name': '해군',
                'name_kr': '스타트 덱 해군'
            },
            'STK-05': {
                'set_code': 'STK-05',
                'display_code': 'ST05',
                'name': 'ONE PIECE FILM edition',
                'name_kr': '스타트 덱 ONE PIECE FILM edition'
            },
            'STK-04': {
                'set_code': 'STK-04',
                'display_code': 'ST04',
                'name': '백수 해적단',
                'name_kr': '스타트 덱 백수 해적단'
            },
            'STK-03': {
                'set_code': 'STK-03',
                'display_code': 'ST03',
                'name': '왕의 부하 칠무해',
                'name_kr': '스타트 덱 왕의 부하 칠무해'
            },
            'STK-02': {
                'set_code': 'STK-02',
                'display_code': 'ST02',
                'name': '최악의 세대',
                'name_kr': '스타트 덱 최악의 세대'
            },
            'STK-01': {
                'set_code': 'STK-01',
                'display_code': 'ST01',
                'name': '밀짚모자 일당',
                'name_kr': '스타트 덱 밀짚모자 일당'
            },
            'PROMO': {
                'set_code': 'PROMO',
                'display_code': 'PROMO',
                'name': '프로모션',
                'name_kr': '프로모션'
            },
        }

    def get_series_info(self, series_code):
        """시리즈 코드로 정보 반환"""
        return self.get_all_series_mapping().get(series_code)

    def get_onepiece_series_name(self, series_code):
        """시리즈 코드에 맞는 한국 사이트 시리즈명 반환"""
        series_info = self.get_series_info(series_code)
        if series_info:
            return f"[{series_code}] {series_info['name_kr']}"
        return f'[{series_code}] 알 수 없는 시리즈'

    def setup_onepiece_game_and_set(self, series_code):
        """원피스 게임과 세트 설정"""
        
        series_info = self.get_series_info(series_code)
        if not series_info:
            self.stdout.write(
                self.style.ERROR(f'❌ 알 수 없는 시리즈: {series_code}')
            )
            return None, None
        
        set_code = series_info['set_code']  # OPK-07, STK-14 등
        set_name = series_info['name']
        set_name_kr = series_info['name_kr']
        
        if self.dry_run:
            try:
                onepiece_game = TCGGame.objects.get(name='OnePiece')
                card_set = CardSet.objects.get(game=onepiece_game, set_code=set_code)
                self.stdout.write(f"📋 기존 데이터 확인: [{set_code}] {set_name_kr}")
                return onepiece_game, card_set
            except (TCGGame.DoesNotExist, CardSet.DoesNotExist):
                self.stdout.write(
                    self.style.ERROR('❌ 기본 데이터가 없습니다. --dry-run 없이 먼저 실행해주세요.')
                )
                return None, None
        
        # 원피스 게임 생성/가져오기
        onepiece_game, game_created = TCGGame.objects.get_or_create(
            name='OnePiece',
            defaults={
                'name_kr': '원피스',
                'slug': 'onepiece',
                'is_active': True
            }
        )
        
        if game_created:
            self.stdout.write(f"✅ 게임 생성: {onepiece_game}")
            self.create_onepiece_rarities(onepiece_game)
        
        # 세트 생성/가져오기
        card_set, set_created = CardSet.objects.get_or_create(
            game=onepiece_game,
            set_code=set_code,  # OPK-07, STK-14 형식으로 저장
            defaults={
                'name': set_name,
                'name_kr': set_name_kr,
                'is_active': True
            }
        )
        
        if set_created:
            self.stdout.write(f"✅ 세트 생성: [{set_code}] {set_name_kr}")
        else:
            self.stdout.write(f"📋 기존 세트 사용: [{set_code}] {set_name_kr}")
        
        return onepiece_game, card_set

    def create_onepiece_rarities(self, game):
        """원피스 카드 레어도 생성"""
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
        
        created_count = 0
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
                created_count += 1
        
        if created_count > 0:
            self.stdout.write(f"✅ 레어도 {created_count}개 생성")

    def extract_text_only(self, element):
        """첫 번째 텍스트만 추출"""
        if element:
            text = element.find(text=True)
            return text.strip() if text else ""
        return ""

    def modify_rarity(self, card_number, rarity):
        """카드 번호에 따라 레어도 접두어 조정"""
        match = re.search(r"_P(\d+)", card_number)
        if match:
            p_num = int(match.group(1))
            if p_num == 1:
                return f"P-{rarity}"
            else:
                return f"SP-{rarity}"
        return rarity

    def extract_card_code(self, card_number):
        """카드 코드 추출 (예: OP06-021_P1 → OP06-021)"""
        return re.sub(r"_P\d+", "", card_number)

    def find_onepiece_rarity(self, game, rarity_text):
        """원피스 레어도 찾기"""
        if not rarity_text:
            return None
        
        try:
            return Rarity.objects.get(game=game, rarity_code=rarity_text)
        except Rarity.DoesNotExist:
            # 새 레어도 생성
            if not self.dry_run:
                new_rarity, created = Rarity.objects.get_or_create(
                    game=game,
                    rarity_code=rarity_text[:20],
                    defaults={
                        'rarity_name': rarity_text,
                        'rarity_name_kr': rarity_text,
                    }
                )
                if created:
                    self.stdout.write(f"🆕 새 레어도 생성: {new_rarity}")
                return new_rarity
            return None

    def crawl_single_series(self):
        """단일 시리즈 크롤링"""
        
        # 게임과 세트 설정
        onepiece_game, card_set = self.setup_onepiece_game_and_set(self.series_code)
        if not onepiece_game or not card_set:
            return
        
        # 크롤링 수행
        cards_saved, versions_created = self.crawl_onepiece_cards(
            onepiece_game, card_set, self.series_code
        )
        
        # 결과 출력
        self.stdout.write("─" * 50)
        self.stdout.write(self.style.SUCCESS("🎉 크롤링 완료!"))
        if not self.dry_run:
            self.stdout.write(f"📊 신규 카드: {cards_saved}장")
            self.stdout.write(f"📊 신규 버전: {versions_created}개")
            self.stdout.write(f"💾 저장 세트: [{card_set.set_code}] {card_set.name_kr}")

    def crawl_onepiece_cards(self, onepiece_game, card_set, series_code):
        """원피스 카드 크롤링"""
        
        base_url = "https://onepiece-cardgame.kr/cardlist.do"
        headers = {"User-Agent": "Mozilla/5.0"}
        
        # 시리즈명 가져오기
        series_name = self.get_onepiece_series_name(series_code)
        
        cards_saved = 0
        versions_created = 0
        page = 0
        
        self.stdout.write(f"🌐 크롤링 대상: {series_name}")
        self.stdout.write("─" * 50)
        
        while True:
            params = {
                "page": page,
                "size": 20,
                "freewords": "",
                "categories": "",
                "illustrations": "",
                "colors": "",
                "series": series_name
            }
            
            self.stdout.write(f"📄 페이지 {page} 요청 중...")
            
            try:
                response = requests.get(base_url, params=params, headers=headers)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")
                
                card_list_section = soup.select_one(".card_sch_list")
                card_buttons = card_list_section.select("button.item") if card_list_section else []
                
                if not card_buttons:
                    self.stdout.write("✅ 더 이상 카드가 없습니다.")
                    break
                
                for card in card_buttons:
                    # 전체 카드 번호 (data_number로 사용: OP08-001_P1)
                    full_card_number = self.extract_text_only(card.select_one(".cardNumber"))
                    # 기본 카드 코드 (card_number로 사용: OP08-001)
                    card_code = self.extract_card_code(full_card_number)
                    card_name = self.extract_text_only(card.select_one(".cardName"))
                    rarity = self.extract_text_only(card.select_one(".rarity"))
                    card_type = self.extract_text_only(card.select_one(".cardType"))
                    
                    # 레어도 조정
                    adjusted_rarity = self.modify_rarity(full_card_number, rarity)
                    
                    if self.dry_run:
                        self.stdout.write(
                            f"🔍 [{full_card_number}] {card_name} ({adjusted_rarity}) - {card_type}"
                        )
                        continue
                    
                    # 데이터 저장
                    with transaction.atomic():
                        # 레어도 찾기
                        rarity_obj = self.find_onepiece_rarity(onepiece_game, adjusted_rarity)
                        
                        # Card 생성 - data_number로 고유하게 식별
                        card_obj, card_created = Card.objects.get_or_create(
                            game=onepiece_game,
                            set=card_set,
                            data_number=full_card_number,  # OP08-001_P1 (고유 식별자)
                            defaults={
                                'card_number': card_code,  # OP08-001 (표시용)
                                'name': card_name,
                                'name_kr': card_name,
                            }
                        )
                        
                        if card_created:
                            cards_saved += 1
                            self.stdout.write(f"💾 신규 카드: [{full_card_number}] {card_name}")
                        
                        # CardVersion 생성
                        version_lookup = {
                            'card': card_obj,
                            'version_code': 'normal',
                        }
                        
                        # _P1, _P2 등이 있는 경우 special 버전으로 처리
                        if full_card_number != card_code:
                            version_lookup['version_code'] = 'special'
                            version_lookup['display_code'] = full_card_number.replace(card_code, '').strip('_')
                        
                        if rarity_obj:
                            version_lookup['rarity'] = rarity_obj
                        
                        card_version, version_created = CardVersion.objects.get_or_create(
                            **version_lookup,
                            defaults={
                                'version_name': f"{card_type} - {adjusted_rarity}" if card_type else adjusted_rarity,
                            }
                        )
                        
                        if version_created:
                            versions_created += 1
                            self.stdout.write(f"🎨 신규 버전: [{full_card_number}] {card_name} ({adjusted_rarity})")
                
                page += 1
                
                if self.delay > 0:
                    time.sleep(self.delay)
                
            except requests.exceptions.RequestException as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ 네트워크 오류: {e}")
                )
                break
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ 처리 오류: {e}")
                )
                break
        
        return cards_saved, versions_created

    def crawl_all_onepiece_series(self):
        """모든 원피스 시리즈 크롤링"""
        
        all_series = self.get_all_series_mapping()
        
        # 원피스 게임 초기 설정
        if not self.dry_run:
            onepiece_game, game_created = TCGGame.objects.get_or_create(
                name='OnePiece',
                defaults={
                    'name_kr': '원피스',
                    'slug': 'onepiece',
                    'is_active': True
                }
            )
            
            if game_created:
                self.stdout.write(f"✅ 게임 생성: {onepiece_game}")
                self.create_onepiece_rarities(onepiece_game)
        
        total_series = len(all_series)
        total_cards = 0
        total_versions = 0
        successful_series = 0
        
        self.stdout.write(f"🎯 총 {total_series}개 시리즈 크롤링 시작!")
        self.stdout.write("=" * 60)
        
        for current_index, (series_code, series_info) in enumerate(all_series.items(), 1):
            
            set_name_kr = series_info['name_kr']
            set_code = series_info['set_code']
            
            self.stdout.write(f"\n📦 [{current_index}/{total_series}] {set_name_kr} 크롤링 중...")
            self.stdout.write(f"   🌐 시리즈: {series_code}")
            self.stdout.write(f"   💾 세트: {set_code}")
            
            try:
                if not self.dry_run:
                    onepiece_game = TCGGame.objects.get(name='OnePiece')
                    onepiece_game, card_set = self.setup_onepiece_game_and_set(series_code)
                    
                    if not onepiece_game or not card_set:
                        raise Exception("게임 또는 세트 설정 실패")
                    
                    cards_saved, versions_created = self.crawl_onepiece_cards(
                        onepiece_game, card_set, series_code
                    )
                else:
                    cards_saved, versions_created = 0, 0
                    self.stdout.write(f"🧪 DRY RUN: {series_code} 처리 스킵")
                
                total_cards += cards_saved
                total_versions += versions_created
                successful_series += 1
                
                self.stdout.write(
                    self.style.SUCCESS(f"✅ {set_name_kr} 완료 - 카드: {cards_saved}장, 버전: {versions_created}개")
                )
                
                if current_index < total_series and self.delay > 0:
                    self.stdout.write(f"⏱️ {self.delay}초 대기...")
                    time.sleep(self.delay)
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ {set_name_kr} 실패: {e}")
                )
                continue
        
        # 최종 결과
        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS("🎉 모든 시리즈 크롤링 완료!"))
        self.stdout.write(f"📊 성공한 시리즈: {successful_series}/{total_series}")
        
        if not self.dry_run:
            self.stdout.write(f"📊 총 카드: {total_cards}장")
            self.stdout.write(f"📊 총 버전: {versions_created}개")