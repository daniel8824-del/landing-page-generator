"""
네이버 쇼핑 API + DataLab 시장 리서치 (async)
"""
import os
import re
import asyncio
import httpx
from datetime import datetime, timedelta

NAVER_CLIENT_ID = os.environ.get("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET", "")
NAVER_HEADERS = {
    "X-Naver-Client-Id": NAVER_CLIENT_ID,
    "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
}

CATEGORY_MAP = {
    "패션": "50000000", "의류": "50000000",
    "잡화": "50000001", "액세서리": "50000001",
    "화장품": "50000002", "뷰티": "50000002",
    "디지털": "50000003", "전자": "50000003", "가전": "50000003",
    "가구": "50000004", "인테리어": "50000004",
    "식품": "50000006", "건강": "50000009",
    "생활": "50000008", "출산": "50000005", "육아": "50000005",
    "스포츠": "50000007", "레저": "50000007",
}


def _has_naver_keys() -> bool:
    return bool(NAVER_CLIENT_ID and NAVER_CLIENT_SECRET)


def _detect_category(items: list, user_category: str = "") -> str:
    if user_category:
        for keyword, code in CATEGORY_MAP.items():
            if keyword in user_category:
                return code
    if items:
        cats = {}
        for item in items:
            for cat_field in ["category1", "category2"]:
                c = item.get(cat_field, "")
                if c:
                    for keyword, code in CATEGORY_MAP.items():
                        if keyword in c:
                            cats[code] = cats.get(code, 0) + 1
        if cats:
            return max(cats, key=cats.get)
    return "50000000"


async def search_products(query: str, display: int = 40, sort: str = "sim") -> list:
    if not _has_naver_keys():
        return []
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(
                "https://openapi.naver.com/v1/search/shop.json",
                params={"query": query, "display": display, "sort": sort},
                headers=NAVER_HEADERS,
            )
            resp.raise_for_status()
            return resp.json().get("items", [])
        except Exception as e:
            print(f"[Naver] search error: {e}")
            return []


async def get_keyword_trend(query: str, category_code: str) -> dict:
    if not _has_naver_keys():
        return {}
    end = datetime.now()
    start = end - timedelta(days=365)
    body = {
        "startDate": start.strftime("%Y-%m-%d"),
        "endDate": end.strftime("%Y-%m-%d"),
        "timeUnit": "month",
        "category": category_code,
        "keyword": [{"name": query, "param": [query]}],
    }
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.post(
                "https://openapi.naver.com/v1/datalab/shopping/category/keywords",
                json=body,
                headers=NAVER_HEADERS,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return {}


async def get_keyword_demographics(query: str, category_code: str) -> dict:
    if not _has_naver_keys():
        return {}
    end = datetime.now()
    start = end - timedelta(days=365)
    results = {}
    async with httpx.AsyncClient(timeout=10) as client:
        for endpoint, key in [("age", "age"), ("gender", "gender")]:
            body = {
                "startDate": start.strftime("%Y-%m-%d"),
                "endDate": end.strftime("%Y-%m-%d"),
                "timeUnit": "month",
                "category": category_code,
                "keyword": [{"name": query, "param": [query]}],
            }
            try:
                resp = await client.post(
                    f"https://openapi.naver.com/v1/datalab/shopping/category/keyword/{endpoint}",
                    json=body,
                    headers=NAVER_HEADERS,
                )
                resp.raise_for_status()
                results[key] = resp.json()
            except Exception:
                results[key] = {}
    return results


async def analyze_market(product_name: str, category: str = "",
                         output_dir: str = "") -> str:
    if not _has_naver_keys():
        return ""

    items = await search_products(product_name)
    if not items:
        return ""

    category_code = _detect_category(items, category)

    prices = []
    for item in items:
        try:
            p = int(item.get("lprice", 0))
            if p > 0:
                prices.append(p)
        except (ValueError, TypeError):
            pass
    prices.sort()
    avg_price = sum(prices) // len(prices) if prices else 0
    min_price = prices[0] if prices else 0
    max_price = prices[-1] if prices else 0
    median_price = prices[len(prices) // 2] if prices else 0

    trend_data, demo_data = await asyncio.gather(
        get_keyword_trend(product_name, category_code),
        get_keyword_demographics(product_name, category_code),
    )

    brands = {}
    for item in items:
        brand = item.get("brand", "") or item.get("maker", "") or "기타"
        brands[brand] = brands.get(brand, 0) + 1
    top_brands = sorted(brands.items(), key=lambda x: -x[1])[:10]

    def clean(text):
        return re.sub(r"<[^>]+>", "", str(text))

    lines = [
        f"# 시장 분석: {product_name}\n",
        f"검색일: {datetime.now().strftime('%Y-%m-%d')}\n",
        f"\n## 가격 분석 (상위 {len(prices)}개 상품)",
        f"- 최저가: {min_price:,}원",
        f"- 최고가: {max_price:,}원",
        f"- 평균가: {avg_price:,}원",
        f"- 중앙값: {median_price:,}원\n",
        "\n## 주요 브랜드",
    ]
    for brand, count in top_brands:
        lines.append(f"- {clean(brand)}: {count}건")

    lines.append("\n## 상위 10개 경쟁 상품")
    for i, item in enumerate(items[:10], 1):
        title = clean(item.get("title", ""))
        price = item.get("lprice", "N/A")
        mall = item.get("mallName", "")
        lines.append(f"{i}. **{title}** — {price}원 ({mall})")

    if trend_data.get("results"):
        lines.append("\n## 12개월 검색 트렌드")
        for result in trend_data["results"]:
            for d in result.get("data", []):
                lines.append(f"- {d.get('period', '')}: {d.get('ratio', '')}")

    if demo_data.get("age", {}).get("results"):
        lines.append("\n## 연령대별 관심도")
        for result in demo_data["age"]["results"]:
            for d in result.get("data", []):
                lines.append(f"- {d.get('group', '')}: {d.get('ratio', '')}")

    if demo_data.get("gender", {}).get("results"):
        lines.append("\n## 성별 관심도")
        for result in demo_data["gender"]["results"]:
            for d in result.get("data", []):
                lines.append(f"- {d.get('group', '')}: {d.get('ratio', '')}")

    content = "\n".join(lines)

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, "00-market.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    return content
