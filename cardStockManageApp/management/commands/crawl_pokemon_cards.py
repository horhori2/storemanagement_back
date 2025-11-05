# my_app/management/commands/crawl_pokemon_cards.py

import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
import time

from cardStockManageApp.models import TCGGame, CardSet, Rarity, Card, CardVersion, Price


class Command(BaseCommand):
    help = '모든 포켓몬 카드 세트를 한번에 크롤링합니다'

    def add_arguments(self, parser):
        parser.add_argument(
            '--start',
            type=int,
            default=1,
            help='시작 카드 번호 (기본값: 1)'
        )
        parser.add_argument(
            '--end',
            type=int,
            default=1000,
            help='종료 카드 번호 (기본값: 1000)'
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=1.0,
            help='세트 간 대기 시간(초) (기본값: 1.0)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='실제 저장하지 않고 크롤링만 테스트'
        )
        parser.add_argument(
            '--only-sets',
            nargs='+',
            help='특정 세트만 크롤링 (예: --only-sets BS2025007 BS2025008)'
        )
        parser.add_argument(
            '--exclude-sets',
            nargs='+',
            help='특정 세트 제외 (예: --exclude-sets BS2023006 BS2023007)'
        )
        parser.add_argument(
            '--reverse',
            action='store_true',
            help='최신 세트부터 크롤링 (기본: 오래된 순)'
        )

    def handle(self, *args, **options):
        self.start = options['start']
        self.end = options['end']
        self.delay = options['delay']
        self.dry_run = options['dry_run']
        self.only_sets = options.get('only_sets', [])
        self.exclude_sets = options.get('exclude_sets', [])
        self.reverse = options['reverse']

        # sell_price가 None인 경우 0으로 설정
        Price.objects.filter(sell_price__isnull=True).update(sell_price=0)
        Price.objects.filter(buy_price__isnull=True).update(buy_price=0)
        
        if self.dry_run:
            self.stdout.write(
                self.style.WARNING('🧪 DRY RUN 모드: 실제 저장하지 않습니다')
            )
        
        self.stdout.write(
            self.style.SUCCESS('🎯 모든 세트 일괄 크롤링 시작!')
        )
        self.stdout.write(f'   🔢 카드 범위: {self.start}-{self.end}')
        self.stdout.write(f'   ⏱️ 세트 간 대기: {self.delay}초')
        
        try:
            self.crawl_all_sets()
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING('\n⏹️ 사용자에 의해 중단되었습니다')
            )
        except Exception as e:
            raise CommandError(f'크롤링 중 오류 발생: {e}')

    def get_all_set_mapping(self):
        """모든 세트 매핑 정보"""
        return {
            'BS2025009': ('m1L', 'Mega Brave', '메가브레이브'),
            'BS2025010': ('m1S', 'Mega Symphonia', '메가심포니아'),
            'BS2025007': ('sv11B', 'Black Bolt', '블랙볼트'),
            'BS2025008': ('sv11W', 'White Flare', '화이트플레어'),
            'BS2025006': ('sv10', 'Glory of Team Rocket', '로켓단의 영광'),
            'BS2025005': ('sv9a', 'Heat Wave Arena', '열풍의 아레나'),
            'BS2025001': ('sv9', 'Battle Partners', '배틀 파트너즈'),
            'BS2024019': ('sv8a', 'Terastal Festa ex', '테라스탈 페스타 ex'),
            'BS2024017': ('sv8', 'Super Electric Breaker', '초전브레이커'),
            'BS2024016': ('sv7a', 'Paradise Dragona', '낙원드래고나'),
            'BS2024012': ('sv7', 'Stellar Miracle', '스텔라미라클'),
            'BS2024011': ('sv6a', 'Night Wanderer', '나이트원더러'),
            'BS2024008': ('sv6', 'Mask of Change', '변환의 가면'),
            'BS2024007': ('sv5a', 'Crimson Haze', '크림슨헤이즈'),
            'BS2024004': ('sv5K', 'Wild Force', '와일드포스'),
            'BS2024005': ('sv5M', 'Cyber Judge', '사이버저지'),
            'BS2024001': ('sv4a', 'Shiny Treasure ex', '샤이니 트레저 ex'),
            'BS2023021': ('sv4K', 'Ancient Roar', '고대의 포효'),
            'BS2023022': ('sv4M', 'Future Flash', '미래의 일섬'),
            'BS2023020': ('sv3a', 'Raging Surf', '레이징서프'),
            'BS2023015': ('sv3', 'Obsidian Flames', '흑염의 지배자'),
            'BS2023014': ('sv2a', 'Pokemon Card 151', '포켓몬 카드 151'),
            'BS2023011': ('sv2P', 'Snow Hazard', '스노해저드'),
            'BS2023012': ('sv2D', 'Paldea Evolved', '클레이버스트'),
            'BS2023010': ('sv1a', 'Triplet Beat', '트리플렛비트'),
            'BS2023006': ('sv1S', 'Scarlet ex', '스칼렛 ex'),
            'BS2023007': ('sv1V', 'Violet ex', '바이올렛 ex'),
        }

    def get_target_sets(self):
        """크롤링 대상 세트 목록 반환"""
        all_sets = self.get_all_set_mapping()
        
        # 특정 세트만 크롤링
        if self.only_sets:
            target_sets = {}
            for url_code in self.only_sets:
                if url_code in all_sets:
                    target_sets[url_code] = all_sets[url_code]
                else:
                    self.stdout.write(
                        self.style.WARNING(f'⚠️ 알 수 없는 세트 코드: {url_code}')
                    )
            return target_sets
        
        # 제외할 세트가 있는 경우
        if self.exclude_sets:
            target_sets = {}
            for url_code, set_info in all_sets.items():
                if url_code not in self.exclude_sets:
                    target_sets[url_code] = set_info
            return target_sets
        
        # 모든 세트
        return all_sets

    def setup_initial_data(self):
        """초기 데이터 설정"""
        if self.dry_run:
            try:
                pokemon_game = TCGGame.objects.get(name='Pokemon')
                self.stdout.write(f"📋 게임 확인: {pokemon_game}")
                return pokemon_game
            except TCGGame.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR('❌ 포켓몬 게임이 없습니다. 먼저 init_card_sets를 실행하거나 --dry-run 없이 실행해주세요.')
                )
                return None
        
        # 게임 생성/가져오기
        pokemon_game, game_created = TCGGame.objects.get_or_create(
            name='Pokemon',
            defaults={
                'name_kr': '포켓몬',
                'slug': 'pokemon',
                'is_active': True
            }
        )
        
        if game_created:
            self.stdout.write(f"✅ 게임 생성: {pokemon_game}")
            self.create_basic_rarities(pokemon_game)
        else:
            self.stdout.write(f"📋 기존 게임 사용: {pokemon_game}")
        
        return pokemon_game

    def create_basic_rarities(self, game):
        """기본 레어도 생성"""
        basic_rarities = [
            ('C', 'Common', '커먼'),
            ('U', 'Uncommon', '언커먼'),
            ('R', 'Rare', '레어'),
            ('RR', 'Double Rare', '더블레어'),
            ('RRR', 'Triple Rare', '트리플레어'),
            ('SR', 'Secret Rare', '시크릿레어'),
            ('SSR', 'Super Secret Rare', '슈퍼시크릿레어'),
            ('HR', 'Hyper Rare', '하이퍼레어'),
            ('AR', 'Art Rare', '아트레어'),
            ('SAR', 'Special Art Rare', '스페셜아트레어'),
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

    def crawl_all_sets(self):
        """모든 세트 크롤링"""
        
        # 초기 데이터 설정
        pokemon_game = self.setup_initial_data()
        if not pokemon_game:
            return
        
        # 대상 세트 목록
        target_sets = self.get_target_sets()
        if not target_sets:
            self.stdout.write(
                self.style.ERROR('❌ 크롤링할 세트가 없습니다.')
            )
            return
        
        # 순서 정렬 (최신순 또는 오래된순)
        sorted_sets = list(target_sets.items())
        if self.reverse:
            sorted_sets.sort(reverse=True)  # 최신순 (BS2025007 먼저)
            self.stdout.write("📅 최신 세트부터 크롤링")
        else:
            sorted_sets.sort()  # 오래된순 (BS2023006 먼저)
            self.stdout.write("📅 오래된 세트부터 크롤링")
        
        # 전체 통계
        total_sets = len(sorted_sets)
        total_cards_saved = 0
        total_versions_created = 0
        successful_sets = 0
        failed_sets = 0
        
        self.stdout.write(f"\n🎯 총 {total_sets}개 세트 크롤링 시작!")
        self.stdout.write("=" * 60)
        
        for current_index, (url_code, (set_code, set_name, set_name_kr)) in enumerate(sorted_sets, 1):
            
            self.stdout.write(f"\n📦 [{current_index}/{total_sets}] {set_name_kr} 크롤링 중...")
            self.stdout.write(f"   🌐 URL: {url_code}")
            self.stdout.write(f"   💾 세트: {set_code}")
            
            try:
                # 개별 세트 크롤링
                cards_saved, versions_created = self.crawl_single_set(
                    pokemon_game, url_code, set_code, set_name, set_name_kr
                )
                
                total_cards_saved += cards_saved
                total_versions_created += versions_created
                successful_sets += 1
                
                self.stdout.write(
                    self.style.SUCCESS(f"✅ {set_name_kr} 완료 - 카드: {cards_saved}장, 버전: {versions_created}개")
                )
                
            except Exception as e:
                failed_sets += 1
                self.stdout.write(
                    self.style.ERROR(f"❌ {set_name_kr} 실패: {e}")
                )
                continue
            
            # 마지막 세트가 아니면 대기
            if current_index < total_sets:
                self.stdout.write(f"⏱️ {self.delay}초 대기...")
                time.sleep(self.delay)
        
        # 최종 결과
        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS("🎉 모든 세트 크롤링 완료!"))
        self.stdout.write(f"📊 성공한 세트: {successful_sets}/{total_sets}")
        self.stdout.write(f"📊 실패한 세트: {failed_sets}/{total_sets}")
        
        if not self.dry_run:
            self.stdout.write(f"📊 총 카드: {total_cards_saved}장")
            self.stdout.write(f"📊 총 버전: {total_versions_created}개")

    def crawl_single_set(self, pokemon_game, url_code, set_code, set_name, set_name_kr):
        """개별 세트 크롤링"""
        
        # 세트 생성/가져오기
        if not self.dry_run:
            card_set, set_created = CardSet.objects.get_or_create(
                game=pokemon_game,
                set_code=set_code,
                defaults={
                    'name': set_name,
                    'name_kr': set_name_kr,
                    'is_active': True
                }
            )
        else:
            try:
                card_set = CardSet.objects.get(game=pokemon_game, set_code=set_code)
            except CardSet.DoesNotExist:
                self.stdout.write(f"⚠️ 세트 없음: {set_code}")
                return 0, 0
        
        # 크롤링
        base_url = f'https://pokemoncard.co.kr/cards/detail/{url_code}'
        cards_saved = 0
        versions_created = 0
        
        for i in range(self.start, self.end):
            card_code = f'{i:03d}'
            url = f'{base_url}{card_code}'
            
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 카드 존재 확인
                p_num_span = soup.select_one('span.p_num')
                if not p_num_span:
                    # 카드가 없으면 이 세트 종료
                    break
                
                # 카드 정보 추출
                card_number = p_num_span.get_text().split()[0] if p_num_span else card_code
                card_name_tag = soup.select_one('span.card-hp.title')
                card_name = card_name_tag.get_text(strip=True) if card_name_tag else f'Unknown Card {card_code}'
                rarity_tag = soup.select_one('#no_wrap_by_admin')
                rarity_text = rarity_tag.get_text(strip=True) if rarity_tag else ''
                image_tag = soup.select_one('img.feature_image')
                image_url = image_tag['src'] if image_tag and image_tag.has_attr('src') else ''
                
                if self.dry_run:
                    continue
                
                # 데이터 저장
                with transaction.atomic():
                    # 레어도 찾기
                    rarity = self.find_rarity_by_text(pokemon_game, rarity_text) if rarity_text else None
                    
                    # Card 생성
                    card, card_created = Card.objects.get_or_create(
                        game=pokemon_game,
                        set=card_set,
                        card_number=card_number,
                        defaults={
                            'name': card_name,
                            'name_kr': card_name,
                            'image_url': image_url,
                        }
                    )
                    
                    if card_created:
                        cards_saved += 1
                    
                    # CardVersion 생성
                    version_lookup = {'card': card, 'version_code': 'normal'}
                    if rarity:
                        version_lookup['rarity'] = rarity
                    
                    card_version, version_created = CardVersion.objects.get_or_create(
                        **version_lookup,
                        defaults={
                            'image_url': image_url,
                            'version_name': rarity_text if rarity_text else None,
                        }
                    )
                    
                    if version_created:
                        versions_created += 1
                
            except requests.exceptions.RequestException:
                # 네트워크 오류는 무시하고 계속
                continue
            except Exception:
                # 기타 오류도 무시하고 계속
                continue
        
        return cards_saved, versions_created

    def find_rarity_by_text(self, game, rarity_text):
        """레어도 텍스트로 Rarity 객체 찾기"""
        if not rarity_text:
            return None
        
        rarity_mapping = {
            '커먼': 'C', '언커먼': 'U', '레어': 'R',
            '더블레어': 'RR', '트리플레어': 'RRR',
            '시크릿레어': 'SR', '슈퍼시크릿레어': 'SSR',
            '하이퍼레어': 'HR', '아트레어': 'AR',
            '스페셜아트레어': 'SAR',
            'Common': 'C', 'Uncommon': 'U', 'Rare': 'R',
            'Double Rare': 'RR', 'Triple Rare': 'RRR',
            'Secret Rare': 'SR', 'Super Secret Rare': 'SSR',
            'Hyper Rare': 'HR', 'Art Rare': 'AR',
            'Special Art Rare': 'SAR',
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