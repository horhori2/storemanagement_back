# my_app/management/commands/tcg_manager.py

from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.db import transaction
import sys

from cardStockManageApp.models import TCGGame, CardSet, Card, CardVersion


class Command(BaseCommand):
    help = 'TCG 카드 데이터를 통합 관리합니다'

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='action', help='실행할 작업')
        
        # 초기화 명령어
        init_parser = subparsers.add_parser('init', help='모든 게임 세트 초기화')
        init_parser.add_argument('--games', nargs='+', choices=['pokemon', 'onepiece', 'digimon', 'all'], 
                               default=['all'], help='초기화할 게임')
        
        # 크롤링 명령어
        crawl_parser = subparsers.add_parser('crawl', help='카드 데이터 크롤링')
        crawl_parser.add_argument('--game', choices=['pokemon', 'onepiece', 'digimon'], required=True, 
                                help='크롤링할 게임')
        crawl_parser.add_argument('--all', action='store_true', help='모든 세트 크롤링')
        crawl_parser.add_argument('--sets', nargs='+', help='특정 세트만 크롤링')
        crawl_parser.add_argument('--dry-run', action='store_true', help='테스트 모드')
        
        # 상태 확인 명령어
        status_parser = subparsers.add_parser('status', help='현재 데이터 상태 확인')
        status_parser.add_argument('--game', choices=['pokemon', 'onepiece', 'digimon'], 
                                 help='특정 게임만 확인')
        
        # 정리 명령어
        clean_parser = subparsers.add_parser('clean', help='데이터 정리')
        clean_parser.add_argument('--game', choices=['pokemon', 'onepiece', 'digimon'], required=True,
                                help='정리할 게임')
        clean_parser.add_argument('--confirm', action='store_true', help='확인 없이 삭제')

    def handle(self, *args, **options):
        action = options.get('action')
        
        if not action:
            self.print_help()
            return
        
        try:
            if action == 'init':
                self.handle_init(options)
            elif action == 'crawl':
                self.handle_crawl(options)
            elif action == 'status':
                self.handle_status(options)
            elif action == 'clean':
                self.handle_clean(options)
        except Exception as e:
            raise CommandError(f'작업 중 오류 발생: {e}')

    def print_help(self):
        """도움말 출력"""
        self.stdout.write(self.style.SUCCESS('🎯 TCG 카드 데이터 통합 관리 도구\n'))
        
        help_text = """
사용법:
  python manage.py tcg_manager <명령어> [옵션]

명령어:
  📦 init     - 게임 세트 초기화
  🔄 crawl    - 카드 데이터 크롤링  
  📊 status   - 현재 데이터 상태 확인
  🗑️ clean    - 데이터 정리

예시:
  # 모든 게임 세트 초기화
  python manage.py tcg_manager init
  
  # 포켓몬만 초기화
  python manage.py tcg_manager init --games pokemon
  
  # 포켓몬 모든 세트 크롤링
  python manage.py tcg_manager crawl --game pokemon --all
  
  # 원피스 특정 세트 크롤링
  python manage.py tcg_manager crawl --game onepiece --sets OPK-07 OPK-06
  
  # 디지몬 카드 크롤링
  python manage.py tcg_manager crawl --game digimon
  
  # 디지몬 특정 세트 크롤링
  python manage.py tcg_manager crawl --game digimon --sets BT16 EX07
  
  # 데이터 상태 확인
  python manage.py tcg_manager status
  
  # 포켓몬 데이터 정리
  python manage.py tcg_manager clean --game pokemon --confirm
        """
        
        self.stdout.write(help_text)

    def handle_init(self, options):
        """세트 초기화 처리"""
        games = options.get('games', ['all'])
        
        if 'all' in games:
            games = ['pokemon', 'onepiece', 'digimon']
        
        self.stdout.write(self.style.SUCCESS('🎯 TCG 세트 초기화 시작'))
        
        for game in games:
            self.stdout.write(f"\n📦 {game.upper()} 세트 초기화 중...")
            
            try:
                if game == 'pokemon':
                    call_command('init_card_sets')
                elif game == 'onepiece':
                    call_command('init_onepiece_sets')
                elif game == 'digimon':
                    # 디지몬은 크롤링 시 자동으로 세트 생성되므로 별도 init 불필요
                    self.stdout.write("   ℹ️ 디지몬은 크롤링 시 자동으로 세트가 생성됩니다")
                    continue
                
                self.stdout.write(
                    self.style.SUCCESS(f"✅ {game.upper()} 초기화 완료")
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ {game.upper()} 초기화 실패: {e}")
                )

    def handle_crawl(self, options):
        """크롤링 처리"""
        game = options['game']
        crawl_all = options.get('all', False)
        specific_sets = options.get('sets', [])
        dry_run = options.get('dry_run', False)
        
        self.stdout.write(
            self.style.SUCCESS(f'🔄 {game.upper()} 카드 크롤링 시작')
        )
        
        try:
            if game == 'pokemon':
                if crawl_all:
                    call_command('crawl_pokemon_cards', 
                               dry_run=dry_run)
                elif specific_sets:
                    call_command('crawl_pokemon_cards',
                               only_sets=specific_sets,
                               dry_run=dry_run)
                else:
                    call_command('crawl_pokemon_cards', dry_run=dry_run)
                    
            elif game == 'onepiece':
                if crawl_all:
                    call_command('crawl_onepiece_cards', 
                               all_series=True,
                               dry_run=dry_run)
                elif specific_sets:
                    for series_code in specific_sets:
                        call_command('crawl_onepiece_cards',
                                   series_code=series_code,
                                   dry_run=dry_run)
                else:
                    call_command('crawl_onepiece_cards', dry_run=dry_run)
            
            elif game == 'digimon':
                if crawl_all:
                    call_command('crawl_digimon_cards',
                               all=True,
                               dry_run=dry_run)
                elif specific_sets:
                    call_command('crawl_digimon_cards',
                               only_sets=specific_sets,
                               dry_run=dry_run)
                else:
                    call_command('crawl_digimon_cards', dry_run=dry_run)
            
            self.stdout.write(
                self.style.SUCCESS(f"✅ {game.upper()} 크롤링 완료")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ {game.upper()} 크롤링 실패: {e}")
            )

    def handle_status(self, options):
        """데이터 상태 확인"""
        specific_game = options.get('game')
        
        self.stdout.write(self.style.SUCCESS('📊 TCG 데이터 현황\n'))
        
        games = TCGGame.objects.all()
        if specific_game:
            games = games.filter(name__icontains=specific_game)
        
        if not games.exists():
            self.stdout.write(
                self.style.WARNING('❌ 등록된 게임이 없습니다.')
            )
            return
        
        total_sets = 0
        total_cards = 0
        total_versions = 0
        
        for game in games:
            sets = CardSet.objects.filter(game=game)
            cards = Card.objects.filter(game=game)
            versions = CardVersion.objects.filter(card__game=game)
            
            self.stdout.write(f"🎮 {game.name_kr or game.name}")
            self.stdout.write(f"   📦 세트: {sets.count()}개")
            self.stdout.write(f"   🃏 카드: {cards.count()}장")
            self.stdout.write(f"   🎨 버전: {versions.count()}개")
            
            # 세트별 상세 정보
            if sets.exists():
                self.stdout.write("   📋 세트 목록:")
                for card_set in sets.order_by('-created_at')[:5]:  # 최신 5개만
                    set_cards = cards.filter(set=card_set).count()
                    self.stdout.write(f"     └ [{card_set.set_code}] {card_set.name_kr}: {set_cards}장")
                
                if sets.count() > 5:
                    self.stdout.write(f"     └ ... 외 {sets.count() - 5}개 세트")
            
            total_sets += sets.count()
            total_cards += cards.count()
            total_versions += versions.count()
            
            self.stdout.write("")
        
        # 전체 요약
        self.stdout.write("=" * 40)
        self.stdout.write(f"📊 전체 요약:")
        self.stdout.write(f"   🎮 게임: {games.count()}개")
        self.stdout.write(f"   📦 총 세트: {total_sets}개")
        self.stdout.write(f"   🃏 총 카드: {total_cards}장")
        self.stdout.write(f"   🎨 총 버전: {total_versions}개")

    def handle_clean(self, options):
        """데이터 정리"""
        game_name = options['game']
        confirm = options.get('confirm', False)
        
        # 게임명 매핑
        game_mapping = {
            'pokemon': 'Pokemon',
            'onepiece': 'OnePiece',
            'digimon': 'Digimon'
        }
        
        target_game_name = game_mapping.get(game_name.lower())
        if not target_game_name:
            self.stdout.write(
                self.style.ERROR(f'❌ 알 수 없는 게임: {game_name}')
            )
            return
        
        try:
            game = TCGGame.objects.get(name=target_game_name)
        except TCGGame.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'❌ 게임을 찾을 수 없습니다: {target_game_name}')
            )
            return
        
        # 현재 데이터 상태 출력
        sets_count = CardSet.objects.filter(game=game).count()
        cards_count = Card.objects.filter(game=game).count()
        versions_count = CardVersion.objects.filter(card__game=game).count()
        
        self.stdout.write(f"🗑️ {game.name_kr} 데이터 정리")
        self.stdout.write(f"   📦 세트: {sets_count}개")
        self.stdout.write(f"   🃏 카드: {cards_count}장")
        self.stdout.write(f"   🎨 버전: {versions_count}개")
        
        if not confirm:
            self.stdout.write(
                self.style.WARNING('\n⚠️ 모든 데이터가 삭제됩니다!')
            )
            response = input('계속하시겠습니까? (yes/no): ')
            if response.lower() not in ['yes', 'y']:
                self.stdout.write('취소되었습니다.')
                return
        
        # 데이터 삭제
        with transaction.atomic():
            Card.objects.filter(game=game).delete()
            CardSet.objects.filter(game=game).delete()
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ {game.name_kr} 모든 데이터가 삭제되었습니다.')
            )