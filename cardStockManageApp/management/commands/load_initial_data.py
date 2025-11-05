# management/commands/load_initial_data.py
# Django 관리 명령어로 만들어서 사용하는 방법

from django.core.management.base import BaseCommand
from django.db import transaction
from cardStockManageApp.models import TCGGame, Rarity, Price

class Command(BaseCommand):
    help = 'Load initial data for TCG store'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting initial data load...'))

        # sell_price가 None인 경우 0으로 설정
        Price.objects.filter(sell_price__isnull=True).update(sell_price=0)
        Price.objects.filter(buy_price__isnull=True).update(buy_price=0)
        
        # 1. TCG 게임 생성
        games_data = [
            {'name': 'Pokemon', 'name_kr': '포켓몬', 'slug': 'pokemon'},
            {'name': 'OnePiece', 'name_kr': '원피스', 'slug': 'onepiece'},
            {'name': 'Digimon', 'name_kr': '디지몬', 'slug': 'digimon'},
        ]
        
        games = {}
        for game_data in games_data:
            game, created = TCGGame.objects.get_or_create(
                name=game_data['name'],
                defaults=game_data
            )
            games[game_data['name']] = game
            if created:
                self.stdout.write(f'Created game: {game}')
            else:
                self.stdout.write(f'Game already exists: {game}')
        
        # 2. 포켓몬 희귀도 생성 (더 자세한 희귀도 포함)
        pokemon_rarities = [
            {'rarity_code': 'C', 'rarity_name': 'Common', 'rarity_name_kr': '커먼', 'sort_order': 1},
            {'rarity_code': 'UC', 'rarity_name': 'Uncommon', 'rarity_name_kr': '언커먼', 'sort_order': 2},
            {'rarity_code': 'R', 'rarity_name': 'Rare', 'rarity_name_kr': '레어', 'sort_order': 3},
            {'rarity_code': 'RR', 'rarity_name': 'Double Rare', 'rarity_name_kr': '더블레어', 'sort_order': 4},
            {'rarity_code': 'RRR', 'rarity_name': 'Triple Rare', 'rarity_name_kr': '트리플레어', 'sort_order': 5},
            {'rarity_code': 'SR', 'rarity_name': 'Super Rare', 'rarity_name_kr': '슈퍼레어', 'sort_order': 6},
            {'rarity_code': 'HR', 'rarity_name': 'Hyper Rare', 'rarity_name_kr': '하이퍼레어', 'sort_order': 7},
            {'rarity_code': 'UR', 'rarity_name': 'Ultra Rare', 'rarity_name_kr': '울트라레어', 'sort_order': 8},
            {'rarity_code': 'SSR', 'rarity_name': 'Shining Super Rare', 'rarity_name_kr': '샤이닝슈퍼레어', 'sort_order': 9},
            {'rarity_code': 'CHR', 'rarity_name': 'Character Rare', 'rarity_name_kr': '캐릭터레어', 'sort_order': 10},
            {'rarity_code': 'CSR', 'rarity_name': 'Character Super Rare', 'rarity_name_kr': '캐릭터슈퍼레어', 'sort_order': 11},
            {'rarity_code': 'AR', 'rarity_name': 'Art Rare', 'rarity_name_kr': '아트레어', 'sort_order': 12},
            {'rarity_code': 'SAR', 'rarity_name': 'Special Art Rare', 'rarity_name_kr': '스페셜아트레어', 'sort_order': 13},
            {'rarity_code': 'PR', 'rarity_name': 'Prismstar Rare', 'rarity_name_kr': '프리즘스타레어', 'sort_order': 14},
            {'rarity_code': 'TR', 'rarity_name': 'Trainers Rare', 'rarity_name_kr': '트레이너스레어', 'sort_order': 15},
            {'rarity_code': 'S', 'rarity_name': 'Shiny', 'rarity_name_kr': '색이 다른', 'sort_order': 16},
            {'rarity_code': 'K', 'rarity_name': 'Kagayaku', 'rarity_name_kr': '찬란한', 'sort_order': 17},
            {'rarity_code': 'A', 'rarity_name': 'Amazing Card', 'rarity_name_kr': '어메이징', 'sort_order': 18},
            {'rarity_code': 'BWR', 'rarity_name': 'Black White Rare', 'rarity_name_kr': '블랙화이트레어', 'sort_order': 19},
        ]
        
        self.create_rarities(games['Pokemon'], pokemon_rarities, 'Pokemon')
        
        # 3. 원피스 희귀도 생성
        onepiece_rarities = [
            {'rarity_code': 'C', 'rarity_name': 'Common', 'rarity_name_kr': '커먼', 'sort_order': 1},
            {'rarity_code': 'UC', 'rarity_name': 'Uncommon', 'rarity_name_kr': '언커먼', 'sort_order': 2},
            {'rarity_code': 'R', 'rarity_name': 'Rare', 'rarity_name_kr': '레어', 'sort_order': 3},
            {'rarity_code': 'SR', 'rarity_name': 'Super Rare', 'rarity_name_kr': '슈퍼레어', 'sort_order': 4},
            {'rarity_code': 'L', 'rarity_name': 'Leader', 'rarity_name_kr': '리더', 'sort_order': 5},
            {'rarity_code': 'P', 'rarity_name': 'Parallel', 'rarity_name_kr': '패러렐', 'sort_order': 6},
            {'rarity_code': 'SP', 'rarity_name': 'Special', 'rarity_name_kr': '스페셜', 'sort_order': 7},
            {'rarity_code': 'SEC', 'rarity_name': 'Secret', 'rarity_name_kr': '시크릿', 'sort_order': 8},
        ]
        
        self.create_rarities(games['OnePiece'], onepiece_rarities, 'OnePiece')
        
        # 4. 디지몬 희귀도 생성
        digimon_rarities = [
            {'rarity_code': 'C', 'rarity_name': 'Common', 'rarity_name_kr': '커먼', 'sort_order': 1},
            {'rarity_code': 'U', 'rarity_name': 'Uncommon', 'rarity_name_kr': '언커먼', 'sort_order': 2},
            {'rarity_code': 'R', 'rarity_name': 'Rare', 'rarity_name_kr': '레어', 'sort_order': 3},
            {'rarity_code': 'SR', 'rarity_name': 'Super Rare', 'rarity_name_kr': '슈퍼레어', 'sort_order': 4},
            {'rarity_code': 'SEC', 'rarity_name': 'Secret', 'rarity_name_kr': '시크릿', 'sort_order': 5},
            {'rarity_code': 'P', 'rarity_name': 'Parallel', 'rarity_name_kr': '패러렐', 'sort_order': 6},
            {'rarity_code': 'PP', 'rarity_name': 'ParallelParallel', 'rarity_name_kr': '희소', 'sort_order': 7},
        ]
        
        self.create_rarities(games['Digimon'], digimon_rarities, 'Digimon')
        
        self.stdout.write(self.style.SUCCESS('Initial data load completed!'))
    
    def create_rarities(self, game, rarities_data, game_name):
        """특정 게임의 희귀도들을 생성"""
        for rarity_data in rarities_data:
            rarity_data['game'] = game
            rarity, created = Rarity.objects.get_or_create(
                game=game,
                rarity_code=rarity_data['rarity_code'],
                defaults=rarity_data
            )
            if created:
                self.stdout.write(f'Created {game_name} rarity: {rarity}')
            else:
                self.stdout.write(f'{game_name} rarity already exists: {rarity}')