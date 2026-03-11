"""
네이버 쇼핑 검색 + 데이터랩 API 모듈
네이버 쇼핑 검색 API와 데이터랩 쇼핑인사이트 API를 활용하여
종합 시장 분석 데이터를 수집한다.

사용 API:
1. 쇼핑 검색 API - 유사 상품 검색, 가격/브랜드/카테고리 수집
2. 데이터랩 분야별 트렌드 - 카테고리 검색 추이
3. 데이터랩 키워드별 트렌드 - 특정 키워드 검색 추이
4. 데이터랩 연령별 트렌드 - 검색 연령 분포
5. 데이터랩 성별 트렌드 - 검색 성별 분포
6. 데이터랩 기기별 트렌드 - 모바일/PC 비율
"""

import os
import re
import statistics
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
import requests
from dotenv import load_dotenv

load_dotenv()

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

# API 엔드포인트
SHOPPING_SEARCH_URL = "https://openapi.naver.com/v1/search/shop.json"
DATALAB_CATEGORY_URL = "https://openapi.naver.com/v1/datalab/shopping/categories"
DATALAB_KEYWORD_URL = "https://openapi.naver.com/v1/datalab/shopping/category/keywords"
DATALAB_AGE_URL = "https://openapi.naver.com/v1/datalab/shopping/category/keyword/age"
DATALAB_GENDER_URL = "https://openapi.naver.com/v1/datalab/shopping/category/keyword/gender"
DATALAB_DEVICE_URL = "https://openapi.naver.com/v1/datalab/shopping/category/device"

# 네이버 쇼핑 카테고리 코드 — 검색 결과 category1 필드와 매핑
CATEGORY_CODE_MAP = {
    "패션의류": "50000000",
    "패션잡화": "50000001",
    "화장품/미용": "50000002",
    "디지털/가전": "50000003",
    "가구/인테리어": "50000004",
    "출산/육아": "50000005",
    "식품": "50000006",
    "스포츠/레저": "50000007",
    "생활/건강": "50000008",
    "여가/생활편의": "50000009",
}

# 퍼지 매칭용 키워드 맵
CATEGORY_KEYWORDS = {
    "50000000": ["패션", "의류", "옷"],
    "50000001": ["패션잡화", "가방", "신발", "액세서리", "잡화"],
    "50000002": ["화장품", "미용", "뷰티", "스킨케어", "메이크업", "코스메틱"],
    "50000003": ["디지털", "가전", "전자", "IT", "컴퓨터", "핸드폰", "노트북", "테크"],
    "50000004": ["가구", "인테리어", "리빙", "홈데코", "수납"],
    "50000005": ["출산", "육아", "유아", "유아동", "아기", "아동", "유모차", "키즈", "베이비"],
    "50000006": ["식품", "음식", "먹거리", "건강식품", "다이어트", "간식"],
    "50000007": ["스포츠", "레저", "운동", "피트니스", "캠핑", "등산", "골프"],
    "50000008": ["생활", "건강", "의료", "헬스", "생활용품", "욕실", "주방"],
    "50000009": ["여가", "문화", "도서", "취미", "반려동물", "펫", "완구"],
}


def _get_headers(content_type=None):
    h = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    if content_type:
        h["Content-Type"] = content_type
    return h


def _strip_html(text):
    return re.sub(r"<[^>]+>", "", text)


def _date_range(months=12):
    today = datetime.now()
    end = today.strftime("%Y-%m-%d")
    start = (today - timedelta(days=30 * months)).strftime("%Y-%m-%d")
    return start, end


# ===== 카테고리 자동 감지 =====

def detect_category_code(search_items, user_category=""):
    """
    검색 결과의 category1 필드에서 카테고리 코드를 자동 감지.
    1순위: 검색 결과에서 가장 많이 나오는 category1
    2순위: 사용자 입력 텍스트로 퍼지 매칭
    """
    # 1순위: 검색 결과 category1에서 자동 감지
    if search_items:
        cat1_list = [item.get("category1", "") for item in search_items if item.get("category1")]
        if cat1_list:
            most_common_cat = Counter(cat1_list).most_common(1)[0][0]
            # 직접 매핑
            if most_common_cat in CATEGORY_CODE_MAP:
                print(f"[OK] 카테고리 자동 감지: '{most_common_cat}' -> {CATEGORY_CODE_MAP[most_common_cat]}")
                return CATEGORY_CODE_MAP[most_common_cat], most_common_cat

            # category1 텍스트로 퍼지 매칭
            code = _fuzzy_match(most_common_cat)
            if code:
                print(f"[OK] 카테고리 퍼지 매칭(검색결과): '{most_common_cat}' -> {code}")
                return code, most_common_cat

    # 2순위: 사용자 입력으로 퍼지 매칭
    if user_category:
        code = _fuzzy_match(user_category)
        if code:
            print(f"[OK] 카테고리 퍼지 매칭(사용자입력): '{user_category}' -> {code}")
            return code, user_category

    print("[WARN] 카테고리 자동 감지 실패")
    return "", ""


def _fuzzy_match(text):
    """키워드 기반 퍼지 매칭"""
    if not text:
        return ""
    input_keywords = re.split(r"[/,\s·\-_]+", text.strip().lower())
    input_keywords = [k for k in input_keywords if len(k) >= 1]

    best_code, best_score = "", 0
    for code, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for ik in input_keywords for ck in keywords if ik in ck or ck in ik)
        if score > best_score:
            best_score = score
            best_code = code

    return best_code if best_score > 0 else ""


def _extract_main_keyword(product_name):
    """제품명에서 DataLab 검색용 핵심 키워드 추출"""
    # 수식어 제거 (프리미엄, 고급, 신형, 2026 등)
    noise = ["프리미엄", "고급", "신형", "최신", "NEW", "new", "특가", "베스트"]
    words = product_name.split()
    keywords = [w for w in words if w not in noise and not w.isdigit()]
    # 마지막 명사가 핵심 키워드인 경우가 많음
    if keywords:
        return keywords[-1] if len(keywords[-1]) >= 2 else " ".join(keywords[-2:])
    return product_name


# ===== API 호출 함수 =====

def search_products(query, display=20, sort="sim"):
    """네이버 쇼핑 검색 API"""
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        print("[FAIL] NAVER API 키가 설정되지 않았습니다.")
        return []

    try:
        r = requests.get(SHOPPING_SEARCH_URL, headers=_get_headers(),
                         params={"query": query, "display": display, "sort": sort}, timeout=10)
        if r.status_code != 200:
            print(f"[FAIL] 쇼핑 검색 API: {r.status_code}")
            return []

        items = r.json().get("items", [])
        results = []
        for item in items:
            results.append({
                "title": _strip_html(item.get("title", "")),
                "link": item.get("link", ""),
                "image": item.get("image", ""),
                "lprice": item.get("lprice", ""),
                "hprice": item.get("hprice", ""),
                "mallName": item.get("mallName", ""),
                "productId": item.get("productId", ""),
                "productType": item.get("productType", ""),
                "brand": item.get("brand", ""),
                "maker": item.get("maker", ""),
                "category1": item.get("category1", ""),
                "category2": item.get("category2", ""),
                "category3": item.get("category3", ""),
                "category4": item.get("category4", ""),
            })

        print(f"[OK] 쇼핑 검색: '{query}' -> {len(results)}개")
        return results
    except Exception as e:
        print(f"[FAIL] 쇼핑 검색 오류: {e}")
        return []


def get_category_trend(category_code):
    """데이터랩 - 분야별 트렌드"""
    start, end = _date_range(12)
    try:
        r = requests.post(DATALAB_CATEGORY_URL,
                          headers=_get_headers("application/json"),
                          json={"startDate": start, "endDate": end, "timeUnit": "month",
                                "category": [{"name": "cat", "param": [category_code]}]},
                          timeout=10)
        if r.status_code == 200:
            print(f"[OK] 카테고리 트렌드 조회 완료")
            return r.json()
    except Exception as e:
        print(f"[FAIL] 카테고리 트렌드: {e}")
    return {}


def get_keyword_trend(category_code, keyword):
    """데이터랩 - 키워드별 트렌드"""
    start, end = _date_range(12)
    try:
        r = requests.post(DATALAB_KEYWORD_URL,
                          headers=_get_headers("application/json"),
                          json={"startDate": start, "endDate": end, "timeUnit": "month",
                                "category": category_code,
                                "keyword": [{"name": keyword, "param": [keyword]}]},
                          timeout=10)
        if r.status_code == 200:
            print(f"[OK] 키워드 트렌드 조회 완료: '{keyword}'")
            return r.json()
    except Exception as e:
        print(f"[FAIL] 키워드 트렌드: {e}")
    return {}


def get_keyword_age(category_code, keyword):
    """데이터랩 - 연령별 트렌드"""
    start, end = _date_range(3)
    try:
        r = requests.post(DATALAB_AGE_URL,
                          headers=_get_headers("application/json"),
                          json={"startDate": start, "endDate": end, "timeUnit": "month",
                                "category": category_code, "keyword": keyword},
                          timeout=10)
        if r.status_code == 200:
            print(f"[OK] 연령별 트렌드 조회 완료")
            return r.json()
    except Exception as e:
        print(f"[FAIL] 연령별 트렌드: {e}")
    return {}


def get_keyword_gender(category_code, keyword):
    """데이터랩 - 성별 트렌드"""
    start, end = _date_range(3)
    try:
        r = requests.post(DATALAB_GENDER_URL,
                          headers=_get_headers("application/json"),
                          json={"startDate": start, "endDate": end, "timeUnit": "month",
                                "category": category_code, "keyword": keyword},
                          timeout=10)
        if r.status_code == 200:
            print(f"[OK] 성별 트렌드 조회 완료")
            return r.json()
    except Exception as e:
        print(f"[FAIL] 성별 트렌드: {e}")
    return {}


def get_device_trend(category_code):
    """데이터랩 - 기기별 트렌드"""
    start, end = _date_range(3)
    try:
        r = requests.post(DATALAB_DEVICE_URL,
                          headers=_get_headers("application/json"),
                          json={"startDate": start, "endDate": end, "timeUnit": "month",
                                "category": category_code, "device": ""},
                          timeout=10)
        if r.status_code == 200:
            print(f"[OK] 기기별 트렌드 조회 완료")
            return r.json()
    except Exception as e:
        print(f"[FAIL] 기기별 트렌드: {e}")
    return {}


def download_product_images(items, output_dir, max_count=5):
    """검색 결과에서 대표 이미지 다운로드"""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    saved = []
    targets = [i for i in items if i.get("image")][:max_count]
    for idx, item in enumerate(targets, 1):
        url = item["image"]
        ext = Path(url.split("?")[0]).suffix.lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp"):
            ext = ".jpg"
        fp = os.path.join(output_dir, f"competitor_{idx:02d}{ext}")
        try:
            resp = requests.get(url, timeout=15, stream=True)
            if resp.status_code == 200:
                with open(fp, "wb") as f:
                    for chunk in resp.iter_content(8192):
                        f.write(chunk)
                saved.append(fp)
        except Exception:
            pass
    print(f"[OK] 이미지 다운로드: {len(saved)}/{len(targets)}개")
    return saved


# ===== 분석 함수 =====

def _analyze_prices(items, our_price=0):
    prices = []
    for item in items:
        try:
            p = int(item["lprice"])
            if p > 0:
                prices.append(p)
        except (ValueError, TypeError):
            pass
    if not prices:
        return {}

    sorted_p = sorted(prices)
    n = len(sorted_p)
    q1 = sorted_p[n // 4] if n >= 4 else sorted_p[0]
    q2 = sorted_p[n // 2]
    q3 = sorted_p[3 * n // 4] if n >= 4 else sorted_p[-1]

    result = {
        "min": min(prices), "max": max(prices),
        "avg": int(sum(prices) / n),
        "median": int(statistics.median(prices)),
        "count": n,
        "q1": q1, "q2": q2, "q3": q3,
    }

    if our_price > 0:
        if our_price <= q1:
            result["position"] = "저가 (하위 25%)"
        elif our_price <= q2:
            result["position"] = "중저가 (25~50%)"
        elif our_price <= q3:
            result["position"] = "중고가 (50~75%)"
        else:
            result["position"] = "고가 (상위 25%)"
        cheaper = sum(1 for p in prices if p < our_price)
        result["percentile"] = int(cheaper / n * 100)

    return result


def _analyze_brands(items):
    brands = [i["brand"] for i in items if i.get("brand")]
    counts = Counter(brands).most_common(10)
    brand_prices = {}
    for item in items:
        b = item.get("brand", "")
        if b:
            try:
                brand_prices.setdefault(b, []).append(int(item["lprice"]))
            except (ValueError, TypeError):
                pass
    return {
        "counts": dict(counts),
        "avg_prices": {b: int(sum(ps) / len(ps)) for b, ps in brand_prices.items() if ps},
    }


def _extract_keywords(items):
    words = []
    stop = {"의", "를", "을", "이", "가", "에", "는", "은", "한", "및", "등", "용", "형", "세트", "개"}
    for item in items:
        words.extend([w for w in re.findall(r"[가-힣]{2,}", item.get("title", "")) if w not in stop])
        words.extend(re.findall(r"[a-zA-Z]{3,}", item.get("title", "")))
    return [w for w, _ in Counter(words).most_common(20)]


def _parse_age_data(age_data):
    """최근 월 연령별 비율 추출"""
    results = age_data.get("results", [])
    if not results:
        return {}
    data = results[0].get("data", [])
    if not data:
        return {}
    # 마지막 월의 데이터만
    periods = sorted(set(d["period"] for d in data))
    last_period = periods[-1] if periods else ""
    age_map = {}
    label = {"10": "10대", "20": "20대", "30": "30대", "40": "40대", "50": "50대", "60": "60대"}
    for d in data:
        if d["period"] == last_period:
            age_map[label.get(d["group"], d["group"])] = round(d["ratio"], 1)
    return age_map


def _parse_gender_data(gender_data):
    """최근 월 성별 비율 추출"""
    results = gender_data.get("results", [])
    if not results:
        return {}
    data = results[0].get("data", [])
    if not data:
        return {}
    periods = sorted(set(d["period"] for d in data))
    last_period = periods[-1] if periods else ""
    gender_map = {}
    for d in data:
        if d["period"] == last_period:
            label = "여성" if d["group"] == "f" else "남성"
            gender_map[label] = round(d["ratio"], 1)
    return gender_map


def _parse_device_data(device_data):
    """최근 월 기기별 비율 추출"""
    results = device_data.get("results", [])
    if not results:
        return {}
    data = results[0].get("data", [])
    if not data:
        return {}
    periods = sorted(set(d["period"] for d in data))
    last_period = periods[-1] if periods else ""
    device_map = {}
    for d in data:
        if d["period"] == last_period:
            label = "모바일" if d["group"] == "mo" else "PC"
            device_map[label] = round(d["ratio"], 1)
    return device_map


def _parse_trend_data(trend_data):
    """월별 트렌드 데이터 + 요약 추출"""
    results = trend_data.get("results", [])
    if not results:
        return [], ""
    data = results[0].get("data", [])
    if not data:
        return [], ""

    monthly = [(d["period"], round(d["ratio"], 1)) for d in data]

    # 트렌드 요약
    summary = ""
    if len(data) >= 6:
        recent = [d["ratio"] for d in data[-3:]]
        older = [d["ratio"] for d in data[-6:-3]]
        r_avg = sum(recent) / len(recent)
        o_avg = sum(older) / len(older)
        if o_avg > 0:
            change = ((r_avg - o_avg) / o_avg) * 100
            if change > 5:
                summary = f"최근 3개월 검색량 {change:.0f}% 상승 (성장세)"
            elif change < -5:
                summary = f"최근 3개월 검색량 {abs(change):.0f}% 하락 (하락세)"
            else:
                summary = f"최근 3개월 검색량 안정적 (변동 {change:+.0f}%)"

    return monthly, summary


# ===== 통합 시장 분석 =====

def analyze_market(product_name, category="", output_dir="output", our_price=0):
    """
    종합 시장 분석.
    카테고리는 검색 결과에서 자동 감지하므로 사용자가 정확히 입력하지 않아도 됨.

    Returns: 저장된 00-market.md 파일 경로
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    images_dir = os.path.join(output_dir, "competitor_images")

    print(f"[INFO] === 시장 분석 시작: '{product_name}' ===")

    # 1. 쇼핑 검색 (정확도순 20개)
    items = search_products(product_name, display=20, sort="sim")

    # 핵심 키워드 추출 (DataLab용)
    main_keyword = _extract_main_keyword(product_name)
    print(f"[INFO] 핵심 키워드: '{main_keyword}'")

    # 추가 검색 (키워드가 다르면)
    if main_keyword != product_name:
        extra = search_products(main_keyword, display=10, sort="sim")
        seen = {i.get("productId") for i in items if i.get("productId")}
        for item in extra:
            pid = item.get("productId", "")
            if pid and pid not in seen:
                items.append(item)
                seen.add(pid)

    print(f"[INFO] 총 {len(items)}개 상품 수집")

    # 2. 카테고리 자동 감지
    cat_code, cat_name = detect_category_code(items, category)

    # 3. 상품 분석
    price_data = _analyze_prices(items, our_price)
    brand_data = _analyze_brands(items)
    keywords = _extract_keywords(items)
    cat_dist = Counter([i.get("category3") or i.get("category2", "") for i in items if i.get("category2")])
    mall_dist = Counter([i.get("mallName", "") for i in items if i.get("mallName")])

    # 4. DataLab API 호출 (카테고리 감지 성공 시)
    cat_trend, cat_trend_summary = [], ""
    kw_trend, kw_trend_summary = [], ""
    age_data, gender_data, device_data = {}, {}, {}

    if cat_code:
        # 카테고리 트렌드
        raw = get_category_trend(cat_code)
        cat_trend, cat_trend_summary = _parse_trend_data(raw)

        # 키워드 트렌드
        raw = get_keyword_trend(cat_code, main_keyword)
        kw_trend, kw_trend_summary = _parse_trend_data(raw)

        # 연령/성별/기기
        age_data = _parse_age_data(get_keyword_age(cat_code, main_keyword))
        gender_data = _parse_gender_data(get_keyword_gender(cat_code, main_keyword))
        device_data = _parse_device_data(get_device_trend(cat_code))

    # 5. 이미지 다운로드
    image_paths = download_product_images(items, images_dir, max_count=5)

    # ===== 마크다운 보고서 생성 =====
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    L = []  # lines

    L.append(f"# 시장 분석 보고서: {product_name}")
    L.append(f"")
    L.append(f"| 항목 | 값 |")
    L.append(f"|------|-----|")
    L.append(f"| 분석일시 | {now_str} |")
    L.append(f"| 검색 키워드 | {product_name} |")
    L.append(f"| 핵심 키워드 | {main_keyword} |")
    L.append(f"| 감지된 카테고리 | {cat_name} (코드: {cat_code}) |")
    L.append(f"| 수집 상품 수 | {len(items)}개 |")
    L.append(f"")

    # --- 경쟁 상품 ---
    L.append(f"## 1. 경쟁 상품 TOP 10")
    L.append(f"")
    if items:
        L.append("| # | 상품명 | 최저가 | 브랜드 | 판매처 | 세부카테고리 |")
        L.append("|---|--------|--------|--------|--------|------------|")
        for i, item in enumerate(items[:10], 1):
            title = item["title"][:35]
            price = f'{int(item["lprice"]):,}원' if item.get("lprice") else "-"
            brand = item.get("brand") or "-"
            mall = item.get("mallName") or "-"
            cat = item.get("category3") or item.get("category2") or "-"
            L.append(f"| {i} | {title} | {price} | {brand} | {mall} | {cat} |")
    L.append(f"")

    # --- 가격 분석 ---
    L.append(f"## 2. 가격 분석")
    L.append(f"")
    if price_data:
        L.append(f"| 지표 | 값 |")
        L.append(f"|------|-----|")
        L.append(f"| 최저가 | {price_data['min']:,}원 |")
        L.append(f"| 최고가 | {price_data['max']:,}원 |")
        L.append(f"| 평균가 | {price_data['avg']:,}원 |")
        L.append(f"| 중간가 | {price_data['median']:,}원 |")
        L.append(f"| 하위 25% 기준 | {price_data['q1']:,}원 |")
        L.append(f"| 상위 25% 기준 | {price_data['q3']:,}원 |")
        if price_data.get("position"):
            L.append(f"")
            L.append(f"**우리 제품 포지셔닝**: {our_price:,}원 -> **{price_data['position']}** (상위 {100 - price_data['percentile']}%)")
    L.append(f"")

    # --- 브랜드 경쟁 ---
    L.append(f"## 3. 브랜드 경쟁 현황")
    L.append(f"")
    if brand_data["counts"]:
        L.append("| 브랜드 | 상품 수 | 평균 가격 |")
        L.append("|--------|---------|----------|")
        for brand, count in brand_data["counts"].items():
            avg = brand_data["avg_prices"].get(brand, 0)
            L.append(f"| {brand} | {count}개 | {avg:,}원 |" if avg else f"| {brand} | {count}개 | - |")
    L.append(f"")

    # --- 판매처 / 카테고리 분포 ---
    L.append(f"## 4. 판매처 분포")
    L.append(f"")
    for mall, count in mall_dist.most_common(8):
        L.append(f"- {mall}: {count}개")
    L.append(f"")

    L.append(f"## 5. 세부 카테고리 분포")
    L.append(f"")
    for cat, count in cat_dist.most_common(5):
        if cat:
            L.append(f"- {cat}: {count}개")
    L.append(f"")

    # --- 키워드 ---
    L.append(f"## 6. 시장 핵심 키워드")
    L.append(f"")
    if keywords:
        L.append(f"상품명에서 추출한 자주 등장하는 키워드 (마케팅 카피 활용):")
        L.append(f"")
        L.append(f"**{', '.join(keywords[:10])}**")
        if len(keywords) > 10:
            L.append(f"")
            L.append(f"추가: {', '.join(keywords[10:])}")
    L.append(f"")

    # --- 카테고리 트렌드 ---
    L.append(f"## 7. 카테고리 검색 트렌드 (12개월)")
    L.append(f"")
    if cat_trend:
        L.append("| 기간 | 검색 비율 |")
        L.append("|------|----------|")
        for period, ratio in cat_trend[-12:]:
            L.append(f"| {period} | {ratio} |")
        if cat_trend_summary:
            L.append(f"")
            L.append(f"**{cat_trend_summary}**")
    else:
        L.append("데이터 없음")
    L.append(f"")

    # --- 키워드 트렌드 ---
    L.append(f"## 8. '{main_keyword}' 키워드 검색 트렌드 (12개월)")
    L.append(f"")
    if kw_trend:
        L.append("| 기간 | 검색 비율 |")
        L.append("|------|----------|")
        for period, ratio in kw_trend[-12:]:
            L.append(f"| {period} | {ratio} |")
        if kw_trend_summary:
            L.append(f"")
            L.append(f"**{kw_trend_summary}**")
    else:
        L.append("데이터 없음")
    L.append(f"")

    # --- 타겟 고객 프로파일 ---
    L.append(f"## 9. 타겟 고객 프로파일 ('{main_keyword}' 검색자)")
    L.append(f"")

    if age_data:
        L.append(f"### 연령별 검색 비율")
        L.append(f"")
        # 가장 높은 비율 찾기
        top_age = max(age_data, key=age_data.get) if age_data else ""
        L.append("| 연령대 | 검색 비율 | 비고 |")
        L.append("|--------|----------|------|")
        for age, ratio in sorted(age_data.items()):
            note = "** 핵심 타겟 **" if age == top_age else ""
            L.append(f"| {age} | {ratio} | {note} |")
        L.append(f"")

    if gender_data:
        L.append(f"### 성별 검색 비율")
        L.append(f"")
        for gender, ratio in gender_data.items():
            L.append(f"- {gender}: {ratio}")
        top_gender = max(gender_data, key=gender_data.get) if gender_data else ""
        if top_gender:
            L.append(f"- **주요 검색자: {top_gender}**")
        L.append(f"")

    if device_data:
        L.append(f"### 검색 기기")
        L.append(f"")
        for device, ratio in device_data.items():
            L.append(f"- {device}: {ratio}")
        L.append(f"")

    # --- 경쟁사 이미지 ---
    L.append(f"## 10. 경쟁사 대표 이미지")
    L.append(f"")
    if image_paths:
        for idx, path in enumerate(image_paths, 1):
            item = items[idx - 1] if idx - 1 < len(items) else {}
            L.append(f"- `{Path(path).name}` — {item.get('title', '')[:40]}")
    else:
        L.append("이미지 없음")
    L.append(f"")

    # --- 핵심 인사이트 요약 ---
    L.append(f"---")
    L.append(f"")
    L.append(f"## 핵심 인사이트 요약")
    L.append(f"")

    insights = []
    if price_data:
        insights.append(f"- **시장 가격대**: {price_data['min']:,}원 ~ {price_data['max']:,}원 (평균 {price_data['avg']:,}원)")
    if brand_data["counts"]:
        top3 = list(brand_data["counts"].keys())[:3]
        insights.append(f"- **주요 경쟁 브랜드**: {', '.join(top3)}")
    if keywords:
        insights.append(f"- **핵심 마케팅 키워드**: {', '.join(keywords[:5])}")
    if age_data:
        top_age = max(age_data, key=age_data.get)
        insights.append(f"- **핵심 타겟 연령**: {top_age} (비율 {age_data[top_age]})")
    if gender_data:
        top_gender = max(gender_data, key=gender_data.get)
        insights.append(f"- **주요 검색 성별**: {top_gender}")
    if device_data:
        top_device = max(device_data, key=device_data.get)
        insights.append(f"- **주요 검색 기기**: {top_device}")
    if cat_trend_summary:
        insights.append(f"- **카테고리 트렌드**: {cat_trend_summary}")
    if kw_trend_summary:
        insights.append(f"- **키워드 트렌드**: {kw_trend_summary}")
    if mall_dist:
        top_mall = mall_dist.most_common(1)[0][0]
        insights.append(f"- **주요 판매채널**: {top_mall}")

    for ins in insights:
        L.append(ins)
    L.append(f"")

    # 파일 저장
    output_path = os.path.join(output_dir, "00-market.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(L))

    print(f"[OK] === 시장 분석 완료: {output_path} ===")
    return output_path


def test_naver_api():
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        print("[FAIL] API 키 없음")
        return False
    try:
        r = requests.get(SHOPPING_SEARCH_URL, headers=_get_headers(),
                         params={"query": "테스트", "display": 1}, timeout=10)
        if r.status_code == 200:
            print("[OK] 네이버 API 연결 성공!")
            return True
        print(f"[FAIL] {r.status_code}")
        return False
    except Exception as e:
        print(f"[FAIL] {e}")
        return False


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        pname = sys.argv[1]
        cat = sys.argv[2] if len(sys.argv) > 2 else ""
        out = sys.argv[3] if len(sys.argv) > 3 else "output"
        analyze_market(pname, cat, out)
    else:
        test_naver_api()
