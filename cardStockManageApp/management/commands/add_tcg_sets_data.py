# cardStockManageApp/management/commands/add_tcg_data.py

# management command로 만들어서 실행:
# python manage.py add_tcg_sets_data

from datetime import date
from cardStockManageApp.models import TCGGame, CardSet
from django.core.management.base import BaseCommand
from django.db import transaction

class Command(BaseCommand):
    help = '포켓몬, 디지몬, 원피스 최신 부스터팩 추가 커맨드'

    def handle(self, *args, **options):
        """메인 실행 메서드"""
        self.stdout.write("TCG 게임 및 카드 세트 데이터 추가 시작...")
        
        with transaction.atomic():
            # 각 게임별 세트 추가
            self.add_pokemon_sets()
            self.add_onepiece_sets()
            self.add_digimon_sets()
        
        self.stdout.write(self.style.SUCCESS("데이터 추가 완료!"))
        self.stdout.write(f"총 {CardSet.objects.count()}개의 카드 세트가 등록되었습니다.")

        # 게임별 세트 수 출력
        for game in TCGGame.objects.all():
            count = game.sets.count()
            self.stdout.write(f"- {game}: {count}개 세트")

    def add_pokemon_sets(self):
        """포켓몬 카드 세트 추가"""
        try:
            pokemon = TCGGame.objects.get(name__icontains='포켓몬')  # 한글명으로 검색
        except TCGGame.DoesNotExist:
            pokemon = TCGGame.objects.get(name__icontains='pokemon')  # 영문명으로 검색
        
        pokemon_sets = [
            # 최신 세트들
            {
                'set_code': 'sv11B',
                'name': 'Black Bolt',
                'name_kr': '블랙볼트',
                'release_date': date(2025, 8, 1)
            },
            {
                'set_code': 'sv11W',
                'name': 'White Flare',
                'name_kr': '화이트플레어',
                'release_date': date(2025, 8, 1)
            },
            {
                'set_code': 'sv10',
                'name': 'Glory of Team Rocket',
                'name_kr': '로켓단의 영광',
                'release_date': date(2025, 6, 20)
            },
            {
                'set_code': 'sv9a',
                'name': 'Heat Wave Arena',
                'name_kr': '열풍의 아레나',
                'release_date': date(2025, 5, 16)
            },
            {
                'set_code': 'sv9',
                'name': 'Battle Partners',
                'name_kr': '배틀 파트너즈',
                'release_date': date(2025, 3, 21)
            },
            {
                'set_code': 'sv8a',
                'name': 'Terastal Fest ex',
                'name_kr': '테라스탈 페스타 ex',
                'release_date': date(2025, 1, 22)
            },
            {
                'set_code': 'sv8',
                'name': 'Super Electric Breaker',
                'name_kr': '초전브레이커',
                'release_date': date(2024, 11, 27)
            },
            {
                'set_code': 'sv7a',
                'name': 'Paradise Dragona',
                'name_kr': '낙원드래고나',
                'release_date': date(2024, 10, 30)
            },
            {
                'set_code': 'sv7',
                'name': 'Stellar Miracle',
                'name_kr': '스텔라미라클',
                'release_date': date(2024, 9, 6)
            },
            {
                'set_code': 'sv6a',
                'name': 'Night Wanderer',
                'name_kr': '나이트원더러',
                'release_date': date(2024, 8, 9)
            },
            {
                'set_code': 'sv6',
                'name': 'Mask of Change',
                'name_kr': '변환의 가면',
                'release_date': date(2024, 6, 21)
            },
            {
                'set_code': 'sv5a',
                'name': 'Crimson Haze',
                'name_kr': '크림슨헤이즈',
                'release_date': date(2024, 5, 24)
            },
            {
                'set_code': 'sv5K',
                'name': 'Wild Force',
                'name_kr': '와일드포스',
                'release_date': date(2024, 3, 6)
            },
            {
                'set_code': 'sv5M',
                'name': 'Cyber Judge',
                'name_kr': '사이버저지',
                'release_date': date(2024, 3, 6)
            },
            {
                'set_code': 'sv4a',
                'name': 'Shiny Treasure ex',
                'name_kr': '샤이니 트레저 ex',
                'release_date': date(2024, 1, 26)
            },
            {
                'set_code': 'sv4K',
                'name': 'Ancient Roar',
                'name_kr': '고대의 포효',
                'release_date': date(2023, 11, 30)
            },
            {
                'set_code': 'sv4M',
                'name': 'Future Flash',
                'name_kr': '미래의 일섬',
                'release_date': date(2023, 11, 30)
            },
            {
                'set_code': 'sv3a',
                'name': 'Raging Surf',
                'name_kr': '레이징서프',
                'release_date': date(2023, 10, 20)
            },
            {
                'set_code': 'sv3',
                'name': 'Obsidian Flames',
                'name_kr': '흑염의 지배자',
                'release_date': date(2023, 8, 25)
            },
            {
                'set_code': 'sv2a',
                'name': 'Pokemon Card 151',
                'name_kr': '포켓몬 카드 151',
                'release_date': date(2023, 7, 28)
            },
            {
                'set_code': 'sv2P',
                'name': 'Snow Hazard',
                'name_kr': '스노해저드',
                'release_date': date(2023, 6, 14)
            },
            {
                'set_code': 'sv2D',
                'name': 'Paldea Evolved',
                'name_kr': '클레이버스트',
                'release_date': date(2023, 6, 14)
            },
            {
                'set_code': 'sv1a',
                'name': 'Triplet Beat',
                'name_kr': '트리플렛비트',
                'release_date': date(2023, 5, 3)
            },
            {
                'set_code': 'sv1S',
                'name': 'Scarlet ex',
                'name_kr': '스칼렛 ex',
                'release_date': date(2023, 3, 15)
            },
            {
                'set_code': 'sv1V',
                'name': 'Violet ex',
                'name_kr': '바이올렛 ex',
                'release_date': date(2023, 3, 15)
            }
        ]

        for set_data in pokemon_sets:
            card_set, created = CardSet.objects.get_or_create(
                game=pokemon,
                set_code=set_data['set_code'],
                defaults=set_data
            )
            if created:
                self.stdout.write(f"카드 세트 '{card_set.name_kr}' ({card_set.set_code}) 생성됨")

    def add_onepiece_sets(self):
        """원피스 카드 세트 추가"""
        try:
            onepiece = TCGGame.objects.get(name__icontains='원피스')
        except TCGGame.DoesNotExist:
            onepiece = TCGGame.objects.get(name__icontains='piece')
        
        onepiece_sets = [
            {
                'set_code': 'OPK-08',
                'name': 'Two Legends',
                'name_kr': '두 전설',
                'release_date': date(2025, 9, 19)
            },
            {
                'set_code': 'OPK-07',
                'name': '500 Years in the Future',
                'name_kr': '500년 후의 미래',
                'release_date': date(2025, 7, 18)
            },
            {
                'set_code': 'EBK-01',
                'name': 'Memorial Collection',
                'name_kr': '메모리얼 컬렉션',
                'release_date': date(2025, 6, 20)
            },
            {
                'set_code': 'OPK-06',
                'name': 'Wings of the Captain',
                'name_kr': '쌍벽의 패자',
                'release_date': date(2025, 4, 25)
            },
            {
                'set_code': 'OPK-05',
                'name': 'Awakening of the New Era',
                'name_kr': '신시대의 주역',
                'release_date': date(2025, 2, 28)
            },
            {
                'set_code': 'OPK-04',
                'name': 'Kingdoms of Intrigue',
                'name_kr': '모략의 왕국',
                'release_date': date(2024, 12, 20)
            },
            {
                'set_code': 'OPK-03',
                'name': 'Pillars of Strength',
                'name_kr': '강대한 적',
                'release_date': date(2024, 10, 25)
            },
            {
                'set_code': 'OPK-02',
                'name': 'Paramount War',
                'name_kr': '정상결전',
                'release_date': date(2024, 7, 29)
            },
            {
                'set_code': 'OPK-01',
                'name': 'Romance Dawn',
                'name_kr': 'ROMANCE DAWN',
                'release_date': date(2024, 4, 25)
            }
        ]
        
        for set_data in onepiece_sets:
            card_set, created = CardSet.objects.get_or_create(
                game=onepiece,
                set_code=set_data['set_code'],
                defaults=set_data
            )
            if created:
                self.stdout.write(f"카드 세트 '{card_set.name_kr}' ({card_set.set_code}) 생성됨")

    def add_digimon_sets(self):
        """디지몬 카드 세트 추가"""
        try:
            digimon = TCGGame.objects.get(name__icontains='디지몬')
        except TCGGame.DoesNotExist:
            digimon = TCGGame.objects.get(name__icontains='digimon')
        
        digimon_sets = [
            # 최신 부스터팩들
            {
                'set_code': 'BTK-17',
                'name': 'Secret Crisis',
                'name_kr': '시크릿 크라이시스',
                'release_date': date(2025, 8, 22)
            },
            {
                'set_code': 'EXK-06',
                'name': 'Infernal Ascension',
                'name_kr': '인퍼널 어센션',
                'release_date': date(2025, 7, 18)
            },
            {
                'set_code': 'BTK-16',
                'name': 'Beginning Observer',
                'name_kr': 'BEGINNING OBSERVER',
                'release_date': date(2025, 6, 20)
            },
            {
                'set_code': 'BTK-15',
                'name': 'Exceed Apocalypse',
                'name_kr': '익시드 아포칼립스',
                'release_date': date(2025, 4, 18)
            },
            {
                'set_code': 'EXK-05',
                'name': 'Animal Colosseum',
                'name_kr': '애니멀 콜로세움',
                'release_date': date(2025, 3, 19)
            },
            {
                'set_code': 'BTK-14',
                'name': 'Blast Ace',
                'name_kr': '블래스트 에이스',
                'release_date': date(2025, 2, 19)
            },
            {
                'set_code': 'RBK-01',
                'name': 'Resurgence Booster',
                'name_kr': '라이징 윈드',
                'release_date': date(2025, 1, 21)
            },
            {
                'set_code': 'BTK-13',
                'name': 'Versus Royal Knights',
                'name_kr': 'vs 로열 나이츠',
                'release_date': date(2024, 11, 20)
            },
            {
                'set_code': 'EXK-04',
                'name': 'Alternative Being',
                'name_kr': '얼터너티브 비잉',
                'release_date': date(2024, 10, 18)
            },
            {
                'set_code': 'BTK-12',
                'name': 'Across Time',
                'name_kr': '어크로스 타임',
                'release_date': date(2024, 9, 25)
            },
            {
                'set_code': 'BTK-11',
                'name': 'Dimensional Phase',
                'name_kr': '디멘셔널 페이즈',
                'release_date': date(2024, 8, 23)
            },
            {
                'set_code': 'EXK-03',
                'name': 'Draconic Roar',
                'name_kr': '드래곤즈 로어',
                'release_date': date(2024, 7, 19)
            },
            {
                'set_code': 'BTK-10',
                'name': 'Xros Encounter',
                'name_kr': '크로스 인카운터',
                'release_date': date(2024, 6, 21)
            }
        ]
        
        for set_data in digimon_sets:
            card_set, created = CardSet.objects.get_or_create(
                game=digimon,
                set_code=set_data['set_code'],
                defaults=set_data
            )
            if created:
                self.stdout.write(f"카드 세트 '{card_set.name_kr}' ({card_set.set_code}) 생성됨")

# Django shell에서 실행하는 방법:
# python manage.py shell
# exec(open('add_tcg_data.py').read())

# 개별 실행 예시:
# from your_app.models import TCGGame, CardSet
# from datetime import date
# 
# # 포켓몬 게임 찾기
# pokemon = TCGGame.objects.filter(name__icontains='포켓몬').first()
# 
# # 개별 세트 추가
# CardSet.objects.create(
#     game=pokemon,
#     set_code='SV7',
#     name='Stellar Crown',
#     name_kr='스텔라 크라운',
#     release_date=date(2024, 8, 9)
# )

# 또는 management command로 만들어서 실행:
# python manage.py add_tcg_sets_data