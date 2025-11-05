# management/commands/update_pokemon_prices.py
# # 기본 실행 (오늘 날짜로 모든 포켓몬카드 업데이트)
# python manage.py update_pokemon_prices

# # 특정 날짜로 업데이트
# python manage.py update_pokemon_prices --date 2024-12-01

# # 특정 카드만 업데이트
# python manage.py update_pokemon_prices --card-id 123

# # 제한된 수만 업데이트 (테스트용)
# python manage.py update_pokemon_prices --limit 10

# # 가격 비교 시뮬레이션 (실제 업데이트 없이)
# python manage.py update_pokemon_prices --dry-run --limit 10

# # 이미 데이터가 있어도 강제로 업데이트
# python manage.py update_pokemon_prices --force

# # 특정 날짜에 10개만 시뮬레이션
# python manage.py update_pokemon_prices --date 2024-12-01 --limit 10 --dry-run

# # 특정 카드를 특정 날짜로 강제 업데이트
# python manage.py update_pokemon_prices --card-id 123 --date 2024-12-01 --force

# # 시뮬레이션으로 가격 변동 미리 확인
# python manage.py update_pokemon_prices --dry-run --limit 5

# # 도움말 확인
# python manage.py update_pokemon_prices --help

# # 한 개 카드로 테스트
# python manage.py update_pokemon_prices --card-id 1 --dry-run

# # 로그 파일로 저장
# python manage.py update_pokemon_prices --dry-run --limit 5 > test.log 2>&1

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime
import time
from cardStockManageApp.services.pokemon_price_service import PokemonPriceService


class Command(BaseCommand):
    help = '포켓몬카드 일별 최저가 업데이트'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='업데이트할 날짜 (YYYY-MM-DD 형식, 기본값: 오늘)'
        )
        parser.add_argument(
            '--card-id',
            type=int,
            help='특정 카드 버전 ID만 업데이트'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='업데이트할 카드 수 제한'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='실제 업데이트 없이 가격 비교 시뮬레이션만 실행'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='이미 데이터가 있어도 강제로 업데이트'
        )
    
    def handle(self, *args, **options):
        service = PokemonPriceService()
        
        # 날짜 처리
        if options['date']:
            try:
                target_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
            except ValueError:
                self.stdout.write(
                    self.style.ERROR('잘못된 날짜 형식입니다. YYYY-MM-DD 형식을 사용하세요.')
                )
                return
        else:
            target_date = timezone.now().date()
        
        start_time = timezone.now()
        self.stdout.write(
            self.style.SUCCESS(f'포켓몬카드 가격 업데이트 시작: {start_time}')
        )
        
        if options['card_id']:
            # 특정 카드만 처리
            self._handle_single_card(service, options, target_date)
        else:
            # 모든 포켓몬카드 처리
            self._handle_all_cards(service, options, target_date)
        
        end_time = timezone.now()
        duration = end_time - start_time
        self.stdout.write(
            self.style.SUCCESS(f'완료 시간: {end_time} (소요시간: {duration})')
        )
    
    def _handle_single_card(self, service, options, target_date):
        """특정 카드 처리"""
        try:
            from cardStockManageApp.models import CardVersion
            card_version = CardVersion.objects.get(id=options['card_id'])
            
            if options['dry_run']:
                self._dry_run_single_card(service, card_version)
            else:
                self._update_single_card(service, card_version, target_date, options['force'])
                
        except CardVersion.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'카드 버전 ID {options["card_id"]}를 찾을 수 없습니다.')
            )
    
    def _handle_all_cards(self, service, options, target_date):
        """모든 포켓몬카드 처리"""
        if options['dry_run']:
            self._dry_run_all_cards(service, options['limit'])
        else:
            self._update_all_cards(service, target_date, options['limit'], options['force'])
    
    def _dry_run_single_card(self, service, card_version):
        """특정 카드 시뮬레이션"""
        self.stdout.write('DRY RUN 모드: 실제 업데이트하지 않음')
        
        card_name = card_version.card.name_kr or card_version.card.name
        search_keyword, rarity, pokemon_name = service.extract_pokemon_card_info(card_version)
        
        # 현재 가격 가져오기
        current_price = None
        if hasattr(card_version, 'price') and card_version.price:
            current_price = card_version.price.sell_price or card_version.price.online_price
        
        # API 검색
        try:
            items = service.search_naver_api(search_keyword)
            if items:
                min_price, valid_results = service.filter_pokemon_api_results(
                    items, search_keyword, rarity, pokemon_name, debug=True
                )
                if min_price:
                    adjusted_price = int(min_price + service.plus_price)
                    
                    if current_price:
                        price_diff = adjusted_price - int(current_price)
                        if price_diff > 0:
                            price_info = f"{int(current_price)} → {adjusted_price} (+{price_diff})"
                        elif price_diff < 0:
                            price_info = f"{int(current_price)} → {adjusted_price} ({price_diff})"
                        else:
                            price_info = f"{int(current_price)} → {adjusted_price} (변동없음)"
                    else:
                        price_info = f"미설정 → {adjusted_price}"
                    
                    self.stdout.write(f'카드: {card_name}')
                    self.stdout.write(f'가격: {price_info}')
                    self.stdout.write(f'검색어: {search_keyword}')
                else:
                    self.stdout.write(f'카드: {card_name}')
                    self.stdout.write(f'가격: {int(current_price) if current_price else "미설정"} → 검색결과없음')
                    self.stdout.write(f'검색어: {search_keyword}')
            else:
                self.stdout.write(f'카드: {card_name}')
                self.stdout.write(f'가격: {int(current_price) if current_price else "미설정"} → API오류')
                self.stdout.write(f'검색어: {search_keyword}')
        except Exception as e:
            self.stdout.write(f'오류 발생: {str(e)}')
    
    def _dry_run_all_cards(self, service, limit):
        """모든 카드 시뮬레이션"""
        self.stdout.write('DRY RUN 모드: 실제 업데이트하지 않음')
        
        from cardStockManageApp.models import CardVersion
        pokemon_cards = CardVersion.objects.filter(
            card__game__name_kr="포켓몬"
        ).select_related('card', 'card__game', 'card__set', 'rarity', 'price')
        
        if limit:
            pokemon_cards = pokemon_cards[:limit]
        
        count = pokemon_cards.count()
        self.stdout.write(f'업데이트 대상: {count}개 카드')
        self.stdout.write('현재가격 → 예상최저가 형태로 표시됩니다...\n')
        
        for idx, card in enumerate(pokemon_cards, 1):
            card_name = card.card.name_kr or card.card.name
            search_keyword, rarity, pokemon_name = service.extract_pokemon_card_info(card)
            
            # 현재 가격
            current_price = None
            if hasattr(card, 'price') and card.price:
                current_price = card.price.sell_price or card.price.online_price
            
            try:
                items = service.search_naver_api(search_keyword)
                if items:
                    debug_mode = (idx == 1)
                    min_price, valid_results = service.filter_pokemon_api_results(
                        items, search_keyword, rarity, pokemon_name, debug=debug_mode
                    )
                    if min_price:
                        adjusted_price = int(min_price + service.plus_price)
                        
                        if current_price:
                            price_diff = adjusted_price - int(current_price)
                            if price_diff > 0:
                                price_info = f"{int(current_price)} → {adjusted_price} (+{price_diff})"
                            elif price_diff < 0:
                                price_info = f"{int(current_price)} → {adjusted_price} ({price_diff})"
                            else:
                                price_info = f"{int(current_price)} → {adjusted_price} (변동없음)"
                        else:
                            price_info = f"미설정 → {adjusted_price}"
                        
                        self.stdout.write(f'  [{idx:2d}] {card_name} | {price_info} | {search_keyword}')
                    else:
                        price_info = f"{int(current_price) if current_price else '미설정'} → 검색결과없음"
                        self.stdout.write(f'  [{idx:2d}] {card_name} | {price_info} | {search_keyword}')
                else:
                    price_info = f"{int(current_price) if current_price else '미설정'} → API오류"
                    self.stdout.write(f'  [{idx:2d}] {card_name} | {price_info} | {search_keyword}')
                
                time.sleep(0.3)
                
            except Exception as e:
                price_info = f"{int(current_price) if current_price else '미설정'} → 오류"
                self.stdout.write(f'  [{idx:2d}] {card_name} | {price_info} | {search_keyword}')
        
        self.stdout.write(f'\n총 {count}개 카드 시뮬레이션 완료')
    
    def _update_single_card(self, service, card_version, target_date, force):
        """특정 카드 업데이트"""
        if force:
            from cardStockManageApp.models import DailyPriceHistory
            DailyPriceHistory.objects.filter(
                card_version=card_version,
                date=target_date
            ).delete()
        
        result = service.update_pokemon_card_daily_price(card_version, target_date)
        
        if result['success']:
            if result.get('skipped'):
                self.stdout.write(
                    self.style.WARNING(f'건너뜀: {result["card_name"]} - {result["message"]}')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'성공: {result["card_name"]} - {result["lowest_price"]}원'
                    )
                )
        else:
            self.stdout.write(
                self.style.ERROR(f'실패: {result["card_name"]} - {result["error"]}')
            )
    
    def _update_all_cards(self, service, target_date, limit, force):
        """모든 카드 업데이트"""
        if force:
            from cardStockManageApp.models import DailyPriceHistory
            deleted_count = DailyPriceHistory.objects.filter(
                card_version__card__game__name_kr="포켓몬",
                date=target_date
            ).delete()[0]
            self.stdout.write(f'기존 데이터 {deleted_count}개 삭제됨')
        
        if limit:
            from cardStockManageApp.models import CardVersion
            pokemon_cards = CardVersion.objects.filter(
                card__game__name_kr="포켓몬"
            ).select_related('card', 'card__game', 'card__set', 'rarity')[:limit]
            
            results = []
            for idx, card_version in enumerate(pokemon_cards, 1):
                self.stdout.write(f'[{idx}/{limit}] {card_version.card.name_kr or card_version.card.name}')
                
                result = service.update_pokemon_card_daily_price(card_version, target_date)
                results.append(result)
                
                if result['success']:
                    if result.get('skipped'):
                        self.stdout.write('  ↻ 건너뜀')
                    else:
                        self.stdout.write(f'  ✓ {result["lowest_price"]}원')
                else:
                    self.stdout.write(f'  ✗ {result["error"]}')
            
            success_count = sum(1 for r in results if r['success'])
            skipped_count = sum(1 for r in results if r.get('success') and r.get('skipped'))
            created_count = sum(1 for r in results if r.get('success') and r.get('created'))
            
            self.stdout.write(
                self.style.SUCCESS(f'완료: {created_count}개 생성, {skipped_count}개 건너뜀, {success_count}/{len(results)}개 성공')
            )
        else:
            results = service.update_all_pokemon_cards_daily(target_date)
            self.stdout.write(
                self.style.SUCCESS(
                    f'전체 업데이트 완료: {results["created"]}개 생성, {results["skipped"]}개 건너뜀, {results["success"]}/{results["total"]}개 성공'
                )
            )