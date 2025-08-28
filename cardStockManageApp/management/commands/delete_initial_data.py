# management/commands/delete_initial_data.py
# Django 관리 명령어로 만들어서 사용하는 방법

from django.core.management.base import BaseCommand
from django.db import transaction
from cardStockManageApp.models import TCGGame, Rarity

class Command(BaseCommand):
    help = 'Delete initial data for TCG store'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Starting initial data deletion...'))
        
        # 확인 메시지
        confirm = input("Are you sure you want to delete all initial data? Type 'yes' to continue: ")
        if confirm.lower() != 'yes':
            self.stdout.write(self.style.ERROR('Deletion cancelled.'))
            return
        
        # 희귀도 삭제 (외래키 때문에 먼저)
        deleted_rarities = 0
        
        # 포켓몬 희귀도 삭제
        pokemon_rarity_codes = ['C', 'UC', 'R', 'RR', 'RRR', 'SR', 'HR', 'UR', 'SAR']
        try:
            pokemon_game = TCGGame.objects.get(name='Pokemon')
            for code in pokemon_rarity_codes:
                try:
                    rarity = Rarity.objects.get(game=pokemon_game, rarity_code=code)
                    rarity.delete()
                    deleted_rarities += 1
                    self.stdout.write(f'Deleted Pokemon rarity: {code}')
                except Rarity.DoesNotExist:
                    self.stdout.write(f'Pokemon rarity {code} not found')
        except TCGGame.DoesNotExist:
            self.stdout.write('Pokemon game not found')
        
        # 원피스 희귀도 삭제
        onepiece_rarity_codes = ['C', 'UC', 'R', 'SR', 'L', 'P', 'SP', 'SEC']
        try:
            onepiece_game = TCGGame.objects.get(name='One Piece')
            for code in onepiece_rarity_codes:
                try:
                    rarity = Rarity.objects.get(game=onepiece_game, rarity_code=code)
                    rarity.delete()
                    deleted_rarities += 1
                    self.stdout.write(f'Deleted One Piece rarity: {code}')
                except Rarity.DoesNotExist:
                    self.stdout.write(f'One Piece rarity {code} not found')
        except TCGGame.DoesNotExist:
            self.stdout.write('One Piece game not found')
        
        # 디지몬 희귀도 삭제
        digimon_rarity_codes = ['C', 'U', 'R', 'SR', 'SEC', 'P']
        try:
            digimon_game = TCGGame.objects.get(name='Digimon')
            for code in digimon_rarity_codes:
                try:
                    rarity = Rarity.objects.get(game=digimon_game, rarity_code=code)
                    rarity.delete()
                    deleted_rarities += 1
                    self.stdout.write(f'Deleted Digimon rarity: {code}')
                except Rarity.DoesNotExist:
                    self.stdout.write(f'Digimon rarity {code} not found')
        except TCGGame.DoesNotExist:
            self.stdout.write('Digimon game not found')
        
        # TCG 게임 삭제
        deleted_games = 0
        game_names = ['Pokemon', 'One Piece', 'Digimon']
        
        for name in game_names:
            try:
                game = TCGGame.objects.get(name=name)
                game.delete()
                deleted_games += 1
                self.stdout.write(f'Deleted game: {name}')
            except TCGGame.DoesNotExist:
                self.stdout.write(f'Game {name} not found')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Initial data deletion completed! '
                f'Deleted {deleted_games} games and {deleted_rarities} rarities.'
            )
        )


