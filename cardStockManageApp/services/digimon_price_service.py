# services/digimon_price_service.py
import urllib.request
import urllib.parse
import json
import time
import re
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
from ..models import CardVersion, DailyPriceHistory

class DigimonPriceService:
    def __init__(self):
        self.client_id = getattr(settings, 'NAVER_CLIENT_ID', "S_iul25XJKSybg_fiSAc")
        self.client_secret = getattr(settings, 'NAVER_CLIENT_SECRET', "_73PsEM4om")
        self.plus_price = getattr(settings, 'PRICE_ADJUSTMENT', 0)
    
    def extract_digimon_card_info(self, card_version):
        """CardVersion 객체에서 디지몬카드 검색 키워드 및 정보 추출"""
        # 게임 타입 확인 (디지몬카드만 처리)
        game_name = card_version.card.game.name_kr or card_version.card.game.name
        if not game_name or game_name != "디지몬":
            return None, None, None
        
        # 각 필드에서 정보 수집
        card_name = card_version.card.name_kr or card_version.card.name
        rarity_code = card_version.rarity.rarity_code if card_version.rarity else None
        set_name = card_version.card.set.name_kr or card_version.card.set.name
        card_number = card_version.card.card_number  # "BT16-097" 같은 카드 번호
        
        # 희소와 패러렐 여부 확인 (카드명이나 세트명에서)
        full_text = f"{card_name} {set_name}".strip()
        has_rare = "희소" in full_text
        has_parallel = "패러렐" in full_text
        
        # 일반 카드 패턴 매칭 (2자리 또는 3자리 둘 다 지원)
        digimon_match = re.search(r'(EX|BT|ST|RB|LM)\d{1,2}-\d{2,3}', card_number)
        if digimon_match:
            card_number_code = digimon_match.group()
            is_st_card = card_number_code.startswith('ST')
            
            # 희소가 있으면 항상 "희소"만 붙임 (희소 패러렐이어도)
            if has_rare:
                if is_st_card:
                    search_keyword = f"희소 디지몬 {card_number_code}"
                else:
                    search_keyword = f"희소 {card_number_code}"
                return search_keyword, "rare", card_number_code
            # 패러렐만 있는 경우
            elif has_parallel:
                if is_st_card:
                    search_keyword = f"패러렐 디지몬 {card_number_code}"
                else:
                    search_keyword = f"패러렐 {card_number_code}"
                return search_keyword, "parallel", card_number_code
            # 일반 카드
            else:
                if is_st_card:
                    search_keyword = f"디지몬 {card_number_code}"
                    return search_keyword, "st", card_number_code
                else:
                    return card_number_code, "normal", card_number_code
        
        # 프로모 카드 패턴
        promo_match = re.search(r'P-\d{3}', card_number)
        if promo_match:
            card_number_code = promo_match.group()
            
            # 희소가 있으면 항상 "희소"만 붙임 (희소 패러렐이어도)
            if has_rare:
                search_keyword = f"희소 디지몬 {card_number_code}"
                return search_keyword, "rare_promo", card_number_code
            # 패러렐만 있는 경우
            elif has_parallel:
                search_keyword = f"패러렐 디지몬 {card_number_code}"
                return search_keyword, "parallel_promo", card_number_code
            # 일반 프로모 카드
            else:
                search_keyword = f"디지몬 {card_number_code}"
                return search_keyword, "promo", card_number_code
        
        # 패턴이 매칭되지 않은 경우 전체 검색어 구성
        search_parts = ["디지몬카드"]
        if card_name:
            search_parts.append(card_name)
        if rarity_code:
            search_parts.append(rarity_code)
        if set_name:
            search_parts.append(set_name)
        
        search_keyword = " ".join(search_parts)
        return search_keyword, "fallback", None
    
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
    
    def filter_digimon_api_results(self, items, search_keyword, card_type=None, required_card_number=None, debug=False):
        """디지몬카드 API 검색 결과 필터링 (업데이트된 로직)"""
        min_price = None
        valid_results = 0
        filter_match_info = "일반검색"
        
        # 검색 조건 설정
        is_parallel = "패러렐" in search_keyword
        is_rare = "희소" in search_keyword
        card_number = None
        
        # 필터 매칭 정보 설정
        if is_rare:
            filter_match_info = "희소검색"
        elif is_parallel:
            filter_match_info = "패러렐검색"
        
        # 카드 번호 추출 (2자리 또는 3자리 둘 다 지원)
        if is_parallel or is_rare:
            card_match = re.search(r'(EX|BT|ST|RB|LM)\d{1,2}-\d{2,3}', search_keyword)
            card_number = card_match.group() if card_match else None
        elif re.match(r'(EX|BT|ST|RB|LM)\d{1,2}-\d{2,3}', search_keyword):
            card_number = search_keyword
        
        if debug:
            print(f"전체 검색 결과: {len(items)}개")
            print(f"필터링 조건 - 카드번호: {card_number}, 희소: {is_rare}, 패러렐: {is_parallel}")
        
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
            if any(keyword in title for keyword in ['일본', '일본판', 'JP', 'JPN', '일판']):
                if debug:
                    print("  → 일본판으로 제외")
                continue
            
            # 카드 번호 매칭
            if card_number and card_number not in title:
                if debug:
                    print(f"  → 카드번호 매칭 실패: {card_number}")
                continue
            
            # 희소 검색인 경우 - 제품명에 "희소"가 있어야 함
            if is_rare and "희소" not in title:
                if debug:
                    print("  → 희소 키워드 매칭 실패")
                continue
            elif is_rare:
                if debug:
                    print("  ✓ 희소 키워드 매칭 성공")
            
            # 패러렐 검색인 경우 - 제품명에 "패러렐"이 있어야 함  
            if is_parallel and "패러렐" not in title:
                if debug:
                    print("  → 패러렐 키워드 매칭 실패")
                continue
            elif is_parallel:
                if debug:
                    print("  ✓ 패러렐 키워드 매칭 성공")
            
            valid_results += 1
            if debug:
                print(f"  ✓ 유효한 결과: {price}원")
            
            # 최저가 업데이트
            if min_price is None or price < min_price:
                min_price = price
        
        if debug:
            print(f"최종 결과: {valid_results}개 유효, 최저가: {min_price}, 필터: {filter_match_info}")
        
        return min_price, valid_results, filter_match_info
    
    def update_digimon_card_daily_price(self, card_version, target_date=None, debug=False):
        """디지몬카드의 일별 최저가 업데이트"""
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
        search_keyword, card_type, card_number = self.extract_digimon_card_info(card_version)
        
        if not search_keyword:
            return {
                'success': False,
                'card_version_id': card_version.id,
                'card_name': f"{card_version.card.name_kr or card_version.card.name}",
                'error': "디지몬카드 검색 패턴이 없습니다"
            }
        
        if debug:
            print(f"\n=== 카드 정보 ===")
            print(f"검색어: {search_keyword}")
            print(f"카드타입: {card_type}")
            print(f"카드번호: {card_number}")
        
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
        min_price, valid_results, filter_match_info = self.filter_digimon_api_results(
            items, search_keyword, card_type, card_number, debug=debug
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
                'card_type': card_type,
                'card_number': card_number,
                'filter_match_info': filter_match_info
            }
            
        except Exception as e:
            return {
                'success': False,
                'card_version_id': card_version.id,
                'card_name': f"{card_version.card.name_kr or card_version.card.name}",
                'error': f"DB 저장 실패: {str(e)}"
            }
    
    def update_all_digimon_cards_daily(self, target_date=None, debug=False):
        """모든 디지몬카드의 일별 최저가 업데이트"""
        if target_date is None:
            target_date = timezone.now().date()
        
        # 디지몬카드만 필터링
        digimon_cards = CardVersion.objects.filter(
            card__game__name_kr="디지몬"
        ).select_related(
            'card', 'card__game', 'card__set', 'rarity'
        )
        
        results = []
        total_count = digimon_cards.count()
        
        print(f"{target_date} 날짜로 디지몬카드 {total_count}개의 가격을 업데이트합니다...")
        
        for idx, card_version in enumerate(digimon_cards, 1):
            card_display_name = f"{card_version.card.name_kr or card_version.card.name}"
            if card_version.rarity:
                card_display_name += f" ({card_version.rarity.rarity_code})"
            
            print(f"[{idx}/{total_count}] 처리 중: {card_display_name}")
            
            result = self.update_digimon_card_daily_price(card_version, target_date, debug=debug)
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