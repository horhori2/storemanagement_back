# my_app/management/commands/crawl_digimon_cards.py

import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
import time
import re
from collections import defaultdict

from cardStockManageApp.models import TCGGame, CardSet, Rarity, Card, CardVersion, Price


class Command(BaseCommand):
    help = '디지몬 카드 데이터를 크롤링합니다'

    def add_arguments(self, parser):
        parser.add_argument(
            '--start-page',
            type=int,
            default=1,
            help='시작 페이지 번호 (기본값: 1)'
        )
        parser.add_argument(
            '--end-page',
            type=int,
            default=1000,
            help='종료 페이지 번호 (기본값: 1000)'
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=0.5,
            help='세트 간 대기 시간(초) (기본값: 0.5)'
        )
        parser.add_argument(
            '--page-delay',
            type=float,
            default=0.2,
            help='페이지 간 대기 시간(초) (기본값: 0.2)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='실제 저장하지 않고 크롤링만 테스트'
        )
        parser.add_argument(
            '--only-sets',
            nargs='+',
            help='특정 세트만 크롤링 (예: --only-sets BTK-17 EXK-06)'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='모든 세트 크롤링'
        )

    def handle(self, *args, **options):
        self.start_page = options['start_page']
        self.end_page = options['end_page']
        self.delay = options['delay']
        self.page_delay = options['page_delay']
        self.dry_run = options['dry_run']
        self.only_sets = options.get('only_sets', [])
        self.crawl_all = options.get('all', False)
        
        # 카드번호별 저장 횟수 카운터 (패러렐/희소 구분용)
        self.card_counter = defaultdict(int)
        
        if self.dry_run:
            self.stdout.write(
                self.style.WARNING('🧪 DRY RUN 모드: 실제 저장하지 않습니다')
            )
        
        self.stdout.write(
            self.style.SUCCESS('🎯 디지몬 카드 크롤링 시작!')
        )
        self.stdout.write(f'   📄 페이지 범위: {self.start_page}-{self.end_page}')
        self.stdout.write(f'   ⏱️ 세트 간 대기: {self.delay}초')
        self.stdout.write(f'   ⏱️ 페이지 간 대기: {self.page_delay}초')
        
        try:
            self.crawl_digimon_cards()
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING('\n⏹️ 사용자에 의해 중단되었습니다')
            )
        except Exception as e:
            raise CommandError(f'크롤링 중 오류 발생: {e}')

    def setup_initial_data(self):
        """초기 데이터 설정"""
        if self.dry_run:
            try:
                digimon_game = TCGGame.objects.get(name='Digimon')
                self.stdout.write(f"📋 게임 확인: {digimon_game}")
                return digimon_game
            except TCGGame.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR('❌ 디지몬 게임이 없습니다. 먼저 init 명령어를 실행해주세요.')
                )
                return None
        
        # 게임 생성/가져오기
        digimon_game, game_created = TCGGame.objects.get_or_create(
            name='Digimon',
            defaults={
                'name_kr': '디지몬',
                'slug': 'digimon',
                'is_active': True
            }
        )
        
        if game_created:
            self.stdout.write(f"✅ 게임 생성: {digimon_game}")
            self.create_basic_rarities(digimon_game)
        else:
            self.stdout.write(f"📋 기존 게임 사용: {digimon_game}")
        
        return digimon_game

    def create_basic_rarities(self, game):
        """기본 레어도 생성"""
        basic_rarities = [
            ('C', 'Common', '커먼'),
            ('U', 'Uncommon', '언커먼'),
            ('R', 'Rare', '레어'),
            ('SR', 'Super Rare', '슈퍼레어'),
            ('SEC', 'Secret Rare', '시크릿레어'),
            ('P', 'Promo', '프로모'),
            ('PR', 'Promo Rare', '프로모레어'),
            ('L', 'Legend', '레전드'),
            ('DR', 'Dragon Rare', '드래곤레어'),
            ('AC', 'Ace', '에이스'),
        ]
        
        created_count = 0
        for rarity_code, rarity_name, rarity_name_kr in basic_rarities:
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

    def get_set_category_mapping(self):
        """세트별 카테고리 ID 매핑"""
        return {
            'BTK-17': 43359,
            'EXK-06': 42671,
            'BTK-16': 42178,
            'BTK-15': 41534,
            'EXK-05': 40815,
            'BTK-14': 40497,
            'RBK-01': 39800,
            'BTK-13': 39056,
            'EXK-04': 38620,
            'BTK-12': 37672,
            'BTK-11': 36807,
            'EXK-03': 35770,
            'BTK-10': 13687,
            'BTK-09': 12160,
            'EXK-02': 11549,
            'BTK-08': 10406,
            'BTK-07': 8585,
            'EXK-01': 7467,
            'BTK-06': 6128,
            'BTK-05': 5192,
            'BTK-04': 4108,
            'BTK-1.5': 2300,
            'BTK-1.0': 1078,
            'STK-19': 43956,
            'STK-18': 43957,
            'STK-17': 41934,
            'STK-16': 39509,
            'STK-15': 39492,
            'STK-14': 37550,
            'STK-13': 13296,
            'STK-12': 13295,
            'STK-10': 9464,
            'STK-09': 9463,
            'STK-08': 5841,
            'STK-07': 5840,
            'STK-06': 3180,
            'STK-05': 3179,
            'STK-04': 3178,
            'STK-03': 212,
            'STK-02': 239,
            'STK-01': 153,
            'PROMO': 488,
        }

    def extract_set_code(self, card_code):
        """카드번호에서 세트 코드 추출 (예: BT16-013 → BTK-16, EX06-013 → EXK-06)"""
        # BTK-17, EXK-06 형식으로 변환
        match = re.match(r'([A-Z]+)(\d+)', card_code)
        if match:
            prefix = match.group(1)
            number = match.group(2)
            # BT16 -> BTK-16, EX06 -> EXK-06
            return f"{prefix}K-{number}"
        return None

    def crawl_digimon_cards(self):
        """디지몬 카드 크롤링"""
        
        # 초기 데이터 설정
        digimon_game = self.setup_initial_data()
        if not digimon_game:
            return
        
        # 세트별 카테고리 매핑
        set_category_mapping = self.get_set_category_mapping()
        
        # 크롤링 대상 세트 결정
        if self.only_sets:
            target_sets = {k: v for k, v in set_category_mapping.items() if k in self.only_sets}
            if not target_sets:
                self.stdout.write(
                    self.style.ERROR('❌ 지정한 세트를 찾을 수 없습니다.')
                )
                return
        elif self.crawl_all:
            target_sets = set_category_mapping
        else:
            # 기본: 최신 세트만
            first_set = list(set_category_mapping.items())[0]
            target_sets = {first_set[0]: first_set[1]}
        
        self.stdout.write(f"📦 크롤링 대상: {list(target_sets.keys())}")
        
        # 전체 통계
        total_sets = len(target_sets)
        total_cards = 0
        total_versions = 0
        successful_sets = 0
        failed_sets = 0
        
        # 세트별 크롤링
        for set_index, (set_code, category_id) in enumerate(target_sets.items(), 1):
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(f"📦 [{set_index}/{total_sets}] {set_code} 크롤링 중...")
            self.stdout.write(f"   🆔 카테고리 ID: {category_id}")
            
            try:
                cards_saved, versions_created = self.crawl_single_set(
                    digimon_game, set_code, category_id
                )
                
                total_cards += cards_saved
                total_versions += versions_created
                successful_sets += 1
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ {set_code} 완료 - 카드: {cards_saved}장, 버전: {versions_created}개"
                    )
                )
                
            except Exception as e:
                failed_sets += 1
                self.stdout.write(
                    self.style.ERROR(f"❌ {set_code} 실패: {e}")
                )
                continue
            
            # 다음 세트로 넘어가기 전 대기
            if set_index < total_sets:
                self.stdout.write(f"⏱️ {self.delay}초 대기...")
                time.sleep(self.delay)
        
        # 최종 결과
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("🎉 디지몬 카드 크롤링 완료!"))
        self.stdout.write(f"📊 성공한 세트: {successful_sets}/{total_sets}")
        self.stdout.write(f"📊 실패한 세트: {failed_sets}/{total_sets}")
        
        if not self.dry_run:
            self.stdout.write(f"📊 총 카드: {total_cards}장")
            self.stdout.write(f"📊 총 버전: {total_versions}개")

    def crawl_single_set(self, digimon_game, set_code, category_id):
        """개별 세트 크롤링"""
        base_url = "https://digimoncard.co.kr"
        start_url = f"https://digimoncard.co.kr/index.php?mid=cardlist&category={category_id}&page={{}}"
        
        cards_saved = 0
        versions_created = 0
        total_pages = 0
        
        for page_num in range(self.start_page, self.end_page + 1):
            self.stdout.write(f"   📄 [{page_num}페이지] 크롤링 중...")
            
            url = start_url.format(page_num)
            
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                self.stdout.write(f"      ⚠️ 페이지 요청 실패: {e}")
                break
            
            soup = BeautifulSoup(response.text, 'html.parser')
            card_items = soup.select('li.image_lists_item')
            
            if not card_items:
                self.stdout.write("      ✅ 더 이상 카드가 없습니다.")
                break
            
            total_pages += 1
            page_cards = 0
            
            for item in card_items:
                try:
                    # 카드 정보 추출
                    card_data = self.extract_card_data(item, base_url)
                    if not card_data:
                        continue
                    
                    # 데이터 저장
                    if not self.dry_run:
                        saved, created = self.save_card_data(digimon_game, card_data)
                        cards_saved += saved
                        versions_created += created
                    
                    page_cards += 1
                    
                except Exception as e:
                    self.stdout.write(f"      ⚠️ 카드 처리 실패: {e}")
                    continue
            
            self.stdout.write(f"      ✅ {page_cards}개 카드 처리")
            
            # 페이지 간 대기
            if page_num < self.end_page:
                time.sleep(self.page_delay)
        
        return cards_saved, versions_created

    def extract_card_data(self, item, base_url):
        """카드 정보 추출"""
        # 카드 이름 태그
        card_name_tag = item.select_one('.card_name')
        if not card_name_tag:
            return None
        
        card_name_tag_text = card_name_tag.get_text(strip=True)
        
        # 카드번호 추출
        match = re.search(
            r'((BT|EX|ST|RB|TM|DR|AC)\d{1,2}-\d{2,3}|P-\d{2,3}|PR-\d{2,3}|token\w*)',
            card_name_tag_text
        )
        if not match:
            return None
        
        card_code = match.group(1)
        
        # 카드 이름 추출 (카드번호와 레어도 제거)
        name_part = card_name_tag_text.replace(card_code, '', 1).strip()
        card_name = re.sub(r'^(SR|SEC|R|U|C|P|PR|L|DR|AC)\s*', '', name_part)
        
        # 카드 정보 추출
        card_info = item.select_one('.cardinfo_head')
        contents = card_info.contents if card_info else []
        
        card_rarity = contents[3] if len(contents) > 3 else None
        card_type = contents[5] if len(contents) > 5 else None
        card_level = contents[7] if len(contents) > 7 else None
        
        card_rarity_text = card_rarity.get_text(strip=True) if card_rarity else ''
        card_type_text = card_type.get_text(strip=True) if card_type else ''
        card_level_text = ''
        
        # 패러렐 확인
        is_parallel = False
        for content in contents:
            if hasattr(content, 'get_text'):
                text = content.get_text(strip=True)
                if '페러렐' in text or '패러렐' in text:
                    is_parallel = True
                    break
        
        # 카드 타입이 '테이머'나 '옵션'이면 레벨은 빈 값
        if card_type_text not in ['테이머', '옵션']:
            card_level_text = card_level.get_text(strip=True) if card_level else ''
        
        # 이미지 URL
        img_tag = item.select_one('div.card_img img')
        if not img_tag or not img_tag.get('src'):
            return None
        
        img_src = img_tag['src']
        img_url = base_url + img_src if img_src.startswith('/') else img_src
        
        # 카드 카운터 증가 (패러렐/희소 구분용)
        self.card_counter[card_code] += 1
        is_rare_parallel = (self.card_counter[card_code] == 3)
        
        return {
            'card_code': card_code,
            'card_name': card_name,
            'rarity_text': card_rarity_text,
            'card_type': card_type_text,
            'card_level': card_level_text,
            'is_parallel': is_parallel,
            'is_rare_parallel': is_rare_parallel,
            'image_url': img_url,
            'counter': self.card_counter[card_code]
        }

    def save_card_data(self, game, card_data):
        """카드 데이터 저장"""
        cards_saved = 0
        versions_created = 0
        
        with transaction.atomic():
            # 카드번호에서 세트 코드 추출 (BT16-013 형식)
            match = re.match(r'([A-Z]+)(\d+)-', card_data['card_code'])
            if not match:
                return 0, 0
            
            prefix = match.group(1)  # BT, EX, ST 등
            number = match.group(2)  # 16, 06, 8 등
            
            # 숫자를 2자리로 패딩 (8 -> 08)
            number_padded = number.zfill(2)
            
            # BTK-16, EXK-06, BTK-08 형식으로 변환
            set_code_formatted = f"{prefix}K-{number_padded}"
            
            # CardSet 가져오기/생성
            card_set, _ = CardSet.objects.get_or_create(
                game=game,
                set_code=set_code_formatted,
                defaults={
                    'name': f'Digimon {set_code_formatted}',
                    'name_kr': f'디지몬 {set_code_formatted}',
                    'is_active': True
                }
            )
            
            # 카드번호에서 번호 부분만 추출 (예: BT16-013 → 013)
            card_number_match = re.search(r'-(\d{2,3})', card_data['card_code'])
            card_number = card_number_match.group(1) if card_number_match else card_data['card_code']
            
            # Card 생성/가져오기
            card, card_created = Card.objects.get_or_create(
                game=game,
                set=card_set,
                card_number=card_number,
                defaults={
                    'name': card_data['card_name'],
                    'name_kr': card_data['card_name'],
                    'image_url': card_data['image_url'],
                }
            )
            
            if card_created:
                cards_saved += 1
            
            # Rarity 찾기
            rarity = self.find_rarity(game, card_data['rarity_text'])
            
            # 버전 코드 결정
            if card_data['is_rare_parallel']:
                version_code = 'rare_parallel'
                version_name = '희소 패러렐'
            elif card_data['is_parallel']:
                version_code = 'parallel'
                version_name = '패러렐'
            else:
                version_code = 'normal'
                version_name = '일반'
            
            # CardVersion 생성
            version_lookup = {
                'card': card,
                'version_code': version_code,
            }
            if rarity:
                version_lookup['rarity'] = rarity
            
            card_version, version_created = CardVersion.objects.get_or_create(
                **version_lookup,
                defaults={
                    'image_url': card_data['image_url'],
                    'version_name': version_name,
                }
            )
            
            if version_created:
                versions_created += 1
        
        return cards_saved, versions_created

    def find_rarity(self, game, rarity_text):
        """레어도 찾기 또는 생성"""
        if not rarity_text:
            return None
        
        rarity_mapping = {
            '커먼': 'C', '언커먼': 'U', '레어': 'R',
            '슈퍼레어': 'SR', '시크릿레어': 'SEC',
            '프로모': 'P', '프로모레어': 'PR',
            '레전드': 'L', '드래곤레어': 'DR', '에이스': 'AC',
            'Common': 'C', 'Uncommon': 'U', 'Rare': 'R',
            'Super Rare': 'SR', 'Secret Rare': 'SEC',
            'Promo': 'P', 'Promo Rare': 'PR',
            'Legend': 'L', 'Dragon Rare': 'DR', 'Ace': 'AC',
        }
        
        # 정확한 매칭
        if rarity_text in rarity_mapping:
            rarity_code = rarity_mapping[rarity_text]
            try:
                return Rarity.objects.get(game=game, rarity_code=rarity_code)
            except Rarity.DoesNotExist:
                pass
        
        # 새 레어도 생성
        new_rarity, created = Rarity.objects.get_or_create(
            game=game,
            rarity_code=rarity_text[:20],
            defaults={
                'rarity_name': rarity_text,
                'rarity_name_kr': rarity_text,
            }
        )
        return new_rarity