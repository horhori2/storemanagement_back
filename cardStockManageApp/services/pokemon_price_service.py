# services/pokemon_price_service.py
import urllib.request
import urllib.parse
import json
import time
import re
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
from ..models import CardVersion, DailyPriceHistory

class PokemonPriceService:
    def __init__(self):
        self.client_id = getattr(settings, 'NAVER_CLIENT_ID', "S_iul25XJKSybg_fiSAc")
        self.client_secret = getattr(settings, 'NAVER_CLIENT_SECRET', "_73PsEM4om")
        self.plus_price = getattr(settings, 'PRICE_ADJUSTMENT', 0)
    
    def extract_pokemon_card_info(self, card_version):
        """CardVersion 객체에서 포켓몬카드 검색 키워드 및 정보 추출"""
        # 게임 타입 확인 (포켓몬카드만 처리)
        game_name = card_version.card.game.name_kr or card_version.card.game.name
        if not game_name or game_name != "포켓몬":
            return None, None, None
        
        # 각 필드에서 정보 수집
        game_text = f"{game_name}카드"  # "포켓몬카드"
        card_name = card_version.card.name_kr or card_version.card.name  # "님피아ex" 또는 "야나프"
        # rarity_code는 DB에서 가져오지만 사용하지 않음 (extracted_rarity를 대신 사용)
        set_name = card_version.card.set.name_kr or card_version.card.set.name  # "테라스탈페스타ex" 또는 "블랙볼트"
        
        # 전체 텍스트 구성
        full_text = f"{game_text} {card_name}"
        if set_name:
            full_text += f" {set_name}"
        
        # 프로모 카드 확인
        promo_match = re.search(r'P-\d{3}', full_text)
        if promo_match:
            search_keyword = f"{game_text} {promo_match.group()}"
            return search_keyword, None, None
        
        # 띄어쓰기로 구분해서 맨 뒤 단어(확장팩)를 제외하고 레어도 검색
        words = full_text.split()
        if len(words) > 1:
            # 맨 뒤 단어를 제외한 부분에서만 레어도 검색
            search_text = " ".join(words[:-1])
        else:
            search_text = full_text
        
        # 레어도 추출 (맨 뒤 단어 제외) - SSR, HR 추가
        rarity_pattern = r'\b(UR|SSR|SR|RR|RRR|CHR|CSR|BWR|AR|SAR|HR|R|U|C|몬스터볼|마스터볼|이로치)\b'
        rarity_match = re.search(rarity_pattern, search_text)
        extracted_rarity = rarity_match.group(1) if rarity_match else None
        
        # 포켓몬 이름 추출 (레어도 제거 후)
        temp_name = search_text
        if extracted_rarity:
            rarity_index = temp_name.find(extracted_rarity)
            if rarity_index != -1:
                temp_name = temp_name[:rarity_index].strip()
        
        # 특수 패턴 확인 (ex, V, VMAX, VStar)
        has_ex_pattern = bool(re.search(r'\b[가-힣A-Za-z\s]+ex\b', temp_name, re.IGNORECASE))
        has_vmax_pattern = bool(re.search(r'\b[가-힣A-Za-z\s]+(?:VMAX|Vmax|vmax)\b', temp_name, re.IGNORECASE))
        has_vstar_pattern = bool(re.search(r'\b[가-힣A-Za-z\s]+(?:VStar|vstar|VSTAR)\b', temp_name, re.IGNORECASE))
        has_v_pattern = bool(re.search(r'\b[가-힣A-Za-z\s]+V\b(?!\s*(?:MAX|max|Star|star))', temp_name, re.IGNORECASE))
        
        pokemon_name = None
        
        if has_vmax_pattern:
            # VMAX 패턴
            name_match = re.search(r'포켓몬카드\s+(.+?)\s*(?:VMAX|Vmax|vmax)', temp_name, re.IGNORECASE)
            if name_match:
                pokemon_name = name_match.group(1).strip()
        elif has_vstar_pattern:
            # VStar 패턴
            name_match = re.search(r'포켓몬카드\s+(.+?)\s*(?:VStar|vstar|VSTAR)', temp_name, re.IGNORECASE)
            if name_match:
                pokemon_name = name_match.group(1).strip()
        elif has_ex_pattern:
            # ex 패턴 - 전체 이름을 포함하여 매칭
            name_match = re.search(r'포켓몬카드\s+(.+?ex)', temp_name, re.IGNORECASE)
            if name_match:
                pokemon_name = name_match.group(1).strip()
        elif has_v_pattern:
            # V 패턴 (VMAX, VStar가 아닌 순수 V)
            name_match = re.search(r'포켓몬카드\s+(.+?)\s*V\b(?!\s*(?:MAX|max|Star|star))', temp_name, re.IGNORECASE)
            if name_match:
                pokemon_name = name_match.group(1).strip()
        else:
            # 기본 패턴: 포켓몬카드 다음의 모든 텍스트
            name_match = re.search(r'포켓몬카드\s+(.+)', temp_name)
            if name_match:
                pokemon_name = name_match.group(1).strip()
        
        # 일반 카드 검색어 구성
        search_keyword = full_text
        
        return search_keyword, extracted_rarity, pokemon_name
    
    def search_naver_api(self, search_keyword):
        """네이버 쇼핑 API 검색"""
        try:
            enc_text = urllib.parse.quote(search_keyword)
            url = f"https://openapi.naver.com/v1/search/shop?query={enc_text}&sort=sim&exclude=used:rental:cbshop&display=20"
            
            request = urllib.request.Request(url)
            request.add_header("X-Naver-Client-Id", self.client_id)
            request.add_header("X-Naver-Client-Secret", self.client_secret)
            
            response = urllib.request.urlopen(request)
            if response.getcode() == 200:
                result = json.loads(response.read())
                return result.get('items', [])
            else:
                return []
        except Exception as e:
            print(f"API 검색 예외 발생: {e}")
            return []
    
    def filter_pokemon_api_results(self, items, search_keyword, required_rarity=None, required_pokemon_name=None, debug=False):
        """포켓몬카드 API 검색 결과 필터링 (업데이트된 로직)"""
        min_price = None
        valid_results = 0
        filter_match_info = "필터없음"
        
        # 특일 카드 여부 확인
        is_special_day = "특일" in search_keyword
        
        if debug:
            print(f"전체 검색 결과: {len(items)}개")
            print(f"필터링 조건 - 포켓몬명: {required_pokemon_name}, 레어도: {required_rarity}")
        
        for item in items:
            title = item['title']
            price = float(item['lprice'])
            mall_name = item.get('mallName', '')
            
            if debug:
                print(f"검토중: {title} - {price}원 (몰: {mall_name})")
            
            # 제외 몰 필터
            if mall_name in ["화성스토어-TCG-", "네이버", "쿠팡"]:
                if debug:
                    print(f"  → 제외 몰({mall_name})로 제외")
                continue
            
            # 일본판 제외
            if any(keyword in title for keyword in ['일본', '일본판', 'JP', 'JPN']):
                if debug:
                    print("  → 일본판으로 제외")
                continue
            
            # 특일 카드 확인
            if is_special_day and "특일" not in title:
                if debug:
                    print("  → 특일 카드 아님으로 제외")
                continue
            
            # HTML 태그 제거
            clean_title = re.sub(r'<[^>]+>', '', title)
            
            # 포켓몬 이름 매칭
            pokemon_name_matched = False
            if required_pokemon_name:
                # 띄어쓰기 제거하고 비교
                required_name_no_space = re.sub(r'\s+', '', required_pokemon_name)
                title_no_space = re.sub(r'\s+', '', clean_title)
                
                if required_name_no_space.lower() in title_no_space.lower():
                    pokemon_name_matched = True
                    if debug:
                        print(f"  ✓ 포켓몬명 매칭 성공 (띄어쓰기 무시): {required_pokemon_name}")
                else:
                    # 단어별로 매칭 시도 (ex, V, VMAX, VSTAR 제외)
                    required_words = [word for word in required_pokemon_name.split() 
                                     if word.lower() not in ['ex', 'v', 'vmax', 'vstar']]
                    word_matches = sum(1 for word in required_words if word.lower() in clean_title.lower())
                    
                    if word_matches == len(required_words) and len(required_words) > 0:
                        pokemon_name_matched = True
                        if debug:
                            print(f"  ✓ 포켓몬명 매칭 성공 (단어별): {required_words}")
                
                if not pokemon_name_matched:
                    if debug:
                        print(f"  → 포켓몬명 매칭 실패: {required_pokemon_name}")
                    continue
            
            # 레어도 매칭
            rarity_matched = False
            if required_rarity:
                if required_rarity in clean_title:
                    rarity_matched = True
                    if debug:
                        print(f"  ✓ 레어도 매칭 성공: {required_rarity}")
                else:
                    if debug:
                        print(f"  → 레어도 매칭 실패: {required_rarity}")
                    continue
            
            # 모든 필터를 통과한 상품
            valid_results += 1
            if debug:
                print(f"  ✓ 유효한 결과: {price}원")
            
            # 최저가 업데이트
            if min_price is None or price < min_price:
                min_price = price
                
                # 필터 매칭 정보 업데이트
                if pokemon_name_matched and rarity_matched:
                    filter_match_info = "포켓몬명+레어도"
                elif pokemon_name_matched:
                    filter_match_info = "포켓몬명만"
                elif rarity_matched:
                    filter_match_info = "레어도만"
                else:
                    filter_match_info = "필터없음"
        
        if debug:
            print(f"최종 결과: {valid_results}개 유효, 최저가: {min_price}, 필터: {filter_match_info}")
        
        return min_price, valid_results, filter_match_info
    
    def update_pokemon_card_daily_price(self, card_version, target_date=None, debug=False):
        """포켓몬카드의 일별 최저가 업데이트"""
        if target_date is None:
            target_date = timezone.now().date()
        
        # 오늘 날짜에 이미 데이터가 있는지 확인
        existing_data = DailyPriceHistory.objects.filter(
            card_version=card_version,
            date=target_date
        ).first()
        
        if existing_data:
            return {
                'success': True,
                'card_version_id': card_version.id,
                'card_name': f"{card_version.card.name_kr or card_version.card.name}",
                'date': target_date,
                'lowest_price': existing_data.online_lowest_price,
                'skipped': True,
                'message': f"이미 {target_date} 데이터가 존재하여 건너뜀"
            }
        
        # 검색 정보 추출
        search_keyword, rarity, pokemon_name = self.extract_pokemon_card_info(card_version)
        
        if not search_keyword:
            return {
                'success': False,
                'card_version_id': card_version.id,
                'card_name': f"{card_version.card.name_kr or card_version.card.name}",
                'error': "포켓몬카드 검색 패턴이 없습니다"
            }
        
        if debug:
            print(f"\n=== 카드 정보 ===")
            print(f"검색어: {search_keyword}")
            print(f"레어도: {rarity}")
            print(f"포켓몬명: {pokemon_name}")
        
        # API 검색
        items = self.search_naver_api(search_keyword)
        if not items:
            return {
                'success': False,
                'card_version_id': card_version.id,
                'card_name': f"{card_version.card.name_kr or card_version.card.name}",
                'error': f"검색 결과가 없습니다: {search_keyword}"
            }
        
        # 결과 필터링
        min_price, valid_results, filter_match_info = self.filter_pokemon_api_results(
            items, search_keyword, rarity, pokemon_name, debug=debug
        )
        
        if min_price is None:
            return {
                'success': False,
                'card_version_id': card_version.id,
                'card_name': f"{card_version.card.name_kr or card_version.card.name}",
                'error': f"필터링 후 유효한 결과가 없습니다: {search_keyword}"
            }
        
        # 가격 조정
        adjusted_price = Decimal(str(min_price + self.plus_price))
        
        try:
            # DailyPriceHistory 생성
            DailyPriceHistory.objects.create(
                card_version=card_version,
                date=target_date,
                online_lowest_price=adjusted_price
            )
            
            # API 제한 방지
            time.sleep(0.3)
            
            return {
                'success': True,
                'card_version_id': card_version.id,
                'card_name': f"{card_version.card.name_kr or card_version.card.name}",
                'date': target_date,
                'lowest_price': adjusted_price,
                'search_keyword': search_keyword,
                'valid_results': valid_results,
                'created': True,
                'rarity': rarity,
                'pokemon_name': pokemon_name,
                'filter_match_info': filter_match_info
            }
            
        except Exception as e:
            return {
                'success': False,
                'card_version_id': card_version.id,
                'card_name': f"{card_version.card.name_kr or card_version.card.name}",
                'error': f"DB 저장 실패: {str(e)}"
            }
    
    def update_all_pokemon_cards_daily(self, target_date=None, debug=False):
        """모든 포켓몬카드의 일별 최저가 업데이트"""
        if target_date is None:
            target_date = timezone.now().date()
        
        # 포켓몬카드만 필터링
        pokemon_cards = CardVersion.objects.filter(
            card__game__name_kr="포켓몬"
        ).select_related(
            'card', 'card__game', 'card__set', 'rarity'
        )
        
        results = []
        total_count = pokemon_cards.count()
        
        print(f"{target_date} 날짜로 포켓몬카드 {total_count}개의 가격을 업데이트합니다...")
        
        for idx, card_version in enumerate(pokemon_cards, 1):
            card_display_name = f"{card_version.card.name_kr or card_version.card.name}"
            if card_version.rarity:
                card_display_name += f" ({card_version.rarity.rarity_code})"
            
            print(f"[{idx}/{total_count}] 처리 중: {card_display_name}")
            
            result = self.update_pokemon_card_daily_price(card_version, target_date, debug=debug)
            results.append(result)
            
            if result['success']:
                if result.get('skipped'):
                    print(f"  ↻ 건너뜀: {result['message']}")
                else:
                    filter_info = result.get('filter_match_info', '알수없음')
                    print(f"  ✓ 신규 생성: {result['lowest_price']}원 (필터: {filter_info})")
            else:
                print(f"  ✗ 실패: {result['error']}")
        
        # 결과 요약
        success_count = sum(1 for r in results if r['success'])
        skipped_count = sum(1 for r in results if r.get('success') and r.get('skipped'))
        created_count = sum(1 for r in results if r.get('success') and r.get('created'))
        failed_count = total_count - success_count
        
        print(f"\n=== {target_date} 업데이트 완료 ===")
        print(f"전체: {total_count}개")
        print(f"성공: {success_count}개 (신규 생성: {created_count}개, 건너뜀: {skipped_count}개)")
        print(f"실패: {failed_count}개")
        
        return {
            'date': target_date,
            'total': total_count,
            'success': success_count,
            'created': created_count,
            'skipped': skipped_count,
            'failed': failed_count,
            'results': results
        }