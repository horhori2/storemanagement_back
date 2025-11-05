# services/onepiece_price_service.py
import urllib.request
import urllib.parse
import json
import time
import re
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
from ..models import CardVersion, DailyPriceHistory

class OnepiecePriceService:
    def __init__(self):
        self.client_id = getattr(settings, 'NAVER_CLIENT_ID', "S_iul25XJKSybg_fiSAc")
        self.client_secret = getattr(settings, 'NAVER_CLIENT_SECRET', "_73PsEM4om")
        self.plus_price = getattr(settings, 'PRICE_ADJUSTMENT', 0)
    
    def extract_onepiece_card_info(self, card_version):
        """CardVersion 객체에서 원피스카드 검색 키워드 및 정보 추출"""
        # 게임 타입 확인 (원피스카드만 처리)
        game_name = card_version.card.game.name_kr or card_version.card.game.name
        if not game_name or game_name != "원피스":
            return None, None, None
        
        # 각 필드에서 정보 수집
        game_text = f"{game_name}카드"  # "원피스카드"
        card_name = card_version.card.name_kr or card_version.card.name
        rarity_code = card_version.rarity.rarity_code if card_version.rarity else None
        set_name = card_version.card.set.name_kr or card_version.card.set.name
        card_number = card_version.card.card_number  # "OP12-345" 같은 카드 번호
        
        # 전체 텍스트 구성
        full_text = f"{game_text} {card_name}"
        if rarity_code:
            full_text += f" {rarity_code}"
        if card_number:
            full_text += f" {card_number}"
        if set_name:
            full_text += f" {set_name}"
        
        # SP- 패턴 체크 (스페셜 카드로 처리)
        sp_pattern = re.search(r'\bSP-(SP|SEC|R|SR|C|L|U|UC)\b', full_text)
        if sp_pattern:
            # 카드 번호 추출
            card_match = re.search(r'(OP|EB|ST)\d{2}-\d{3}', card_number or full_text)
            if card_match:
                extracted_card_number = card_match.group()
                search_keyword = f"SP {extracted_card_number}"
                return search_keyword, "special", extracted_card_number
            else:
                return None, None, None
        
        # P- 레어도 패턴 확인 (패러렐로 처리)
        has_p_rarity = rarity_code and bool(re.search(r'^P-(SEC|R|SR|C|L|U)$', rarity_code))
        
        # 카드 번호 패턴 찾기
        card_patterns = [
            (r'(OP|EB|ST)\d{2}-\d{3}', 'standard'),  # 일반 카드
            (r'P-\d{3}', 'promo')  # 프로모 카드
        ]
        
        for pattern, card_type in card_patterns:
            match = re.search(pattern, card_number or full_text)
            if match:
                extracted_card_number = match.group()
                
                if card_type == 'promo':
                    search_keyword = f"원피스 {extracted_card_number}"
                    return search_keyword, "promo", extracted_card_number
                elif has_p_rarity:
                    search_keyword = f"패러렐 {extracted_card_number}"
                    return search_keyword, "parallel", extracted_card_number
                elif extracted_card_number.startswith('ST'):
                    search_keyword = f"원피스 {extracted_card_number}"
                    return search_keyword, "st", extracted_card_number
                else:
                    search_keyword = extracted_card_number
                    return search_keyword, "normal", extracted_card_number
        
        # "원피스"로 시작하는 경우 추가 검색
        if full_text.startswith("원피스"):
            other_patterns = [
                (r'OP\d{2}-\d{3}', 'normal'),
                (r'(ST|EB|PR)\d{2}-\d{3}', 'special'),
                (r'P-\d{3}', 'promo')
            ]
            
            for pattern, ptype in other_patterns:
                match = re.search(pattern, full_text)
                if match:
                    extracted_card_number = match.group()
                    
                    if ptype == 'promo' or extracted_card_number.startswith('ST'):
                        search_keyword = f"원피스 {extracted_card_number}"
                    elif has_p_rarity:
                        search_keyword = f"패러렐 {extracted_card_number}"
                    else:
                        search_keyword = extracted_card_number
                    
                    return search_keyword, ptype, extracted_card_number
            
            # 등급 패턴 검색
            grade_match = re.search(r'(SR|R|C|L|SEC)\s+(OP|ST|EB|PR)\d{2}-\d{3}', full_text)
            if grade_match:
                extracted_card_number = grade_match.group(2)
                
                if has_p_rarity:
                    search_keyword = f"패러렐 {extracted_card_number}"
                elif extracted_card_number.startswith('ST'):
                    search_keyword = f"원피스 {extracted_card_number}"
                else:
                    search_keyword = extracted_card_number
                
                return search_keyword, "grade", extracted_card_number
        
        # 매칭되는 패턴이 없으면 전체 검색어 구성
        search_parts = [game_text]
        if card_name:
            search_parts.append(card_name)
        if rarity_code:
            search_parts.append(rarity_code)
        if set_name:
            search_parts.append(set_name)
        search_keyword = " ".join(search_parts)
        
        return search_keyword, "fallback", card_number
    
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
    
    def filter_onepiece_api_results(self, items, search_keyword, card_type=None, required_card_number=None, debug=False):
        """원피스카드 API 검색 결과 필터링 (업데이트된 로직)"""
        min_price = None
        valid_results = 0
        filter_match_info = "일반검색"
        
        # 검색 조건 설정
        is_parallel = "패러렐" in search_keyword
        is_special = "SP" in search_keyword
        
        # 카드 번호 추출
        card_number = None
        if is_special:
            # SP 검색어에서 카드 번호 추출
            card_match = re.search(r'(OP|ST|EB|PR)\d{2}-\d{3}', search_keyword)
            card_number = card_match.group() if card_match else None
            filter_match_info = "스페셜검색"
        elif is_parallel:
            # 패러렐 검색어에서 카드 번호 추출
            card_match = re.search(r'(OP|ST|EB|PR)\d{2}-\d{3}', search_keyword)
            card_number = card_match.group() if card_match else None
            filter_match_info = "패러렐검색"
        elif re.match(r'(OP|ST|EB|PR)\d{2}-\d{3}', search_keyword):
            # 일반 카드 번호
            card_number = search_keyword
            filter_match_info = "일반검색"
        
        if debug:
            print(f"전체 검색 결과: {len(items)}개")
            print(f"필터링 조건 - 카드번호: {card_number}, 패러렐: {is_parallel}, 스페셜: {is_special}")
        
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
            
            # 스페셜 카드 키워드 확인
            if is_special:
                special_keywords = ['스페셜', 'SP']
                if not any(keyword in title for keyword in special_keywords):
                    if debug:
                        print("  → 스페셜 키워드 매칭 실패")
                    continue
                if debug:
                    print("  ✓ 스페셜 키워드 매칭 성공")
            
            # 패러렐 카드 키워드 확인
            elif is_parallel:
                parallel_keywords = ['패러렐', '다른', '패레', 'P시크릿레어', '페러럴', '패러럴', '페러렐', '페레']
                if not any(keyword in title for keyword in parallel_keywords):
                    if debug:
                        print("  → 패러렐 키워드 매칭 실패")
                    continue
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
    
    def update_onepiece_card_daily_price(self, card_version, target_date=None, debug=False):
        """원피스카드의 일별 최저가 업데이트"""
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
        search_keyword, card_type, card_number = self.extract_onepiece_card_info(card_version)
        
        if not search_keyword:
            return {
                'success': False,
                'card_version_id': card_version.id,
                'card_name': f"{card_version.card.name_kr or card_version.card.name}",
                'error': "원피스카드 검색 패턴이 없습니다"
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
        min_price, valid_results, filter_match_info = self.filter_onepiece_api_results(
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
    
    def update_all_onepiece_cards_daily(self, target_date=None, debug=False):
        """모든 원피스카드의 일별 최저가 업데이트"""
        if target_date is None:
            target_date = timezone.now().date()
        
        # 원피스카드만 필터링
        onepiece_cards = CardVersion.objects.filter(
            card__game__name_kr="원피스"
        ).select_related(
            'card', 'card__game', 'card__set', 'rarity'
        )
        
        results = []
        total_count = onepiece_cards.count()
        
        print(f"{target_date} 날짜로 원피스카드 {total_count}개의 가격을 업데이트합니다...")
        
        for idx, card_version in enumerate(onepiece_cards, 1):
            card_display_name = f"{card_version.card.name_kr or card_version.card.name}"
            if card_version.rarity:
                card_display_name += f" ({card_version.rarity.rarity_code})"
            
            print(f"[{idx}/{total_count}] 처리 중: {card_display_name}")
            
            result = self.update_onepiece_card_daily_price(card_version, target_date, debug=debug)
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