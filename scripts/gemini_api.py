"""
Gemini API를 사용하여 상세페이지 섹션 이미지를 생성하는 모듈
Gemini 3 Pro Image Preview 모델 사용

docs/gemini_api.py 참조 기반
"""

import os
import json
import base64
import time
from pathlib import Path
from typing import Optional
import requests
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Gemini 3 Pro Image Preview 모델
MODEL_NAME = "gemini-3-pro-image-preview"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent"


def generate_image(
    prompt: str,
    output_path: str,
    width: int = 1200,
    height: int = 1200
) -> Optional[str]:
    """
    Gemini API를 사용하여 이미지를 생성합니다.

    Args:
        prompt: 이미지 생성 프롬프트
        output_path: 저장할 파일 경로
        width: 이미지 너비
        height: 이미지 높이

    Returns:
        저장된 파일 경로 또는 None (실패시)
    """
    if not GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY not found in .env")
        return None

    # 프롬프트에 크기 정보 및 울트라 리얼리스틱 스타일 강제 추가
    full_prompt = f"""Generate a PHOTOREALISTIC professional image.

=== ABSOLUTE DIMENSION REQUIREMENTS ===
1. EXACT SIZE: {width}x{height} pixels - NO EXCEPTIONS
2. FULL BLEED: Content fills ENTIRE {width}x{height} canvas with NO margins
3. DIMENSION LOCK: Output MUST be exactly {width}x{height} pixels

=== ULTRA-REALISTIC PHOTOGRAPHY STYLE (CRITICAL - MUST FOLLOW) ===

CAMERA QUALITY:
- Shot on professional DSLR (Canon 5D Mark IV / Sony A7R IV quality)
- High resolution, sharp details, professional color grading
- Natural depth of field with beautiful bokeh where appropriate

HUMAN MODELS (when showing people):
- REAL Korean models with NATURAL skin texture
- Visible pores, subtle skin details - NOT airbrushed plastic look
- Professional makeup with glass-skin/dewy finish
- Natural expressions, NOT AI-generated uncanny valley faces
- Individual hair strands visible, professionally styled

PRODUCT PHOTOGRAPHY:
- Luxury cosmetic brand quality
- Realistic reflections, refractions, material textures
- Touchable cream/gel textures
- Accurate glass/plastic light behavior

LIGHTING:
- Professional studio lighting with soft diffusion
- Natural shadows and highlights
- Rim lighting for skin glow effects

STYLE REFERENCE:
- Amorepacific, Sulwhasoo, Laneige flagship advertising
- Vogue Korea beauty editorial
- High-end department store imagery

ABSOLUTELY AVOID:
- Cartoon, illustration, vector art, or graphic design style
- Flat colors or digital art look
- Overly smooth, plastic-looking skin
- Generic stock photo feel
- AI-generated artifacts

=== CONTENT ===
{prompt}

=== KOREAN TEXT RENDERING (CRITICAL) ===
- Use Pretendard Bold font for ALL Korean text (weight 700+)
- NEVER use thin/light weight fonts for Korean text — thick strokes only
- Minimum 28pt equivalent for body text, 48pt+ for headlines
- Every Korean character MUST be a valid, correctly-formed Hangul syllable
- Fewer words rendered perfectly is BETTER than many words rendered poorly

=== FINAL QUALITY CHECKLIST ===
✓ Image is EXACTLY {width}x{height} pixels
✓ Looks like a REAL photograph, not digital art
✓ Skin has realistic texture with visible pores
✓ Lighting creates natural shadows and highlights
✓ Could be mistaken for actual brand advertisement
✓ ALL Korean text is pixel-perfect valid Hangul — zero garbled characters"""

    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "contents": [{
            "parts": [{
                "text": full_prompt
            }]
        }],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"]
        }
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"  Calling API: {MODEL_NAME}" + (f" (retry {attempt+1})" if attempt > 0 else ""))
            response = requests.post(
                f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
                headers=headers,
                json=payload,
                timeout=180
            )

            if response.status_code == 429:
                wait = min(30, 5 * (attempt + 1))
                print(f"  Rate limited (429). Waiting {wait}s before retry...")
                time.sleep(wait)
                continue

            if response.status_code != 200:
                print(f"  Error: API returned status {response.status_code}")
                print(f"  Response: {response.text[:500]}")
                if attempt < max_retries - 1:
                    time.sleep(3)
                    continue
                return None

            result = response.json()
            candidates = result.get("candidates", [])
            if not candidates:
                print("  Error: No candidates in response")
                if attempt < max_retries - 1:
                    time.sleep(3)
                    continue
                return None

            parts = candidates[0].get("content", {}).get("parts", [])

            for part in parts:
                if "inlineData" in part:
                    image_data = part["inlineData"]["data"]
                    mime_type = part["inlineData"].get("mimeType", "image/png")
                    image_bytes = base64.b64decode(image_data)

                    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                    with open(output_path, "wb") as f:
                        f.write(image_bytes)

                    print(f"  [OK] Image saved: {output_path} ({mime_type})")
                    return output_path

            # 이미지가 없으면 텍스트 응답 확인
            for part in parts:
                if "text" in part:
                    print(f"  Text response: {part['text'][:200]}")

            print("  Error: No image data in response")
            if attempt < max_retries - 1:
                time.sleep(3)
                continue
            return None

        except requests.exceptions.Timeout:
            print(f"  Error: Request timed out (180s)")
            if attempt < max_retries - 1:
                continue
            return None
        except requests.exceptions.RequestException as e:
            print(f"  Error: Request failed - {e}")
            if attempt < max_retries - 1:
                time.sleep(3)
                continue
            return None
        except Exception as e:
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()
            return None

    return None


def generate_all_sections(
    prompts_file: str,
    output_dir: str,
    delay_between: float = 3.0
) -> list:
    """
    모든 섹션 이미지를 순차적으로 생성합니다.

    Args:
        prompts_file: gemini_prompts.json 파일 경로
        output_dir: 출력 디렉토리
        delay_between: API 호출 간 대기 시간 (초)

    Returns:
        생성된 이미지 경로 리스트
    """
    with open(prompts_file, "r", encoding="utf-8") as f:
        prompts_data = json.load(f)

    generated_images = []
    total_sections = len(prompts_data)

    for i, (section_key, section_data) in enumerate(prompts_data.items(), 1):
        print(f"\n  [{i}/{total_sections}] Generating {section_key}...")

        prompt = section_data["prompt"]
        width = section_data.get("width", 1200)
        height = section_data.get("height", 600)
        filename = section_data.get("filename", f"{section_key}.png")

        output_path = os.path.join(output_dir, filename)

        result = generate_image(prompt, output_path, width, height)

        if result:
            generated_images.append(result)
        else:
            print(f"  Warning: Failed to generate {section_key}")

        # API 레이트 리밋 방지
        if i < total_sections:
            print(f"  Waiting {delay_between}s before next request...")
            time.sleep(delay_between)

    print(f"\n  Generation complete: {len(generated_images)}/{total_sections} images")
    return generated_images


def generate_all_sections_from_md(
    prompt_file: str,
    output_dir: str,
    delay_between: float = 3.0
) -> list:
    """
    05-prompt.md 파일에서 13개 프롬프트를 파싱하여 이미지를 생성합니다.

    Args:
        prompt_file: 05-prompt.md 파일 경로
        output_dir: 출력 디렉토리
        delay_between: API 호출 간 대기 시간 (초)

    Returns:
        생성된 이미지 경로 리스트
    """
    import re

    content = Path(prompt_file).read_text(encoding="utf-8")

    # ## Section XX 패턴으로 분리
    sections = re.split(r'## Section (\d+)[:\s]', content)

    # 섹션별 높이
    heights = {
        1: 800, 2: 600, 3: 500, 4: 700, 5: 400,
        6: 600, 7: 800, 8: 500, 9: 700, 10: 500,
        11: 400, 12: 400, 13: 600
    }

    section_names = {
        1: "hero", 2: "pain", 3: "problem", 4: "story",
        5: "solution", 6: "how_it_works", 7: "social_proof",
        8: "authority", 9: "benefits", 10: "risk_removal",
        11: "comparison", 12: "target_filter", 13: "final_cta"
    }

    os.makedirs(output_dir, exist_ok=True)
    generated_images = []
    prompts = []

    for i in range(1, len(sections), 2):
        if i + 1 < len(sections):
            num = int(sections[i])
            raw = sections[i + 1].strip()
            prompt_text = re.sub(r'^```\w*\n', '', raw)
            prompt_text = re.sub(r'\n```$', '', prompt_text)
            prompts.append({"num": num, "prompt": prompt_text.strip()})

    total = len(prompts)
    print(f"\n{'='*60}")
    print(f"  Gemini 3 Pro Image Generation")
    print(f"{'='*60}")
    print(f"  Parsed {total} section prompts from {prompt_file}")
    print(f"  API Key: {'[OK] Set' if GEMINI_API_KEY else '[FAIL] Not set'}")
    print()

    for i, section in enumerate(prompts, 1):
        num = section["num"]
        name = section_names.get(num, f"section_{num}")
        height = heights.get(num, 600)
        filename = f"{num:02d}_{name}.png"
        output_path = os.path.join(output_dir, filename)

        print(f"\n  [{i}/{total}] Section {num:02d}: {name} (1200x{height})")

        result = generate_image(section["prompt"], output_path, 1200, height)

        if result:
            generated_images.append(result)
        else:
            print(f"  Warning: Failed to generate section {num:02d}")

        if i < total:
            print(f"  Waiting {delay_between}s...")
            time.sleep(delay_between)

    print(f"\n{'='*60}")
    print(f"  [OK] {len(generated_images)}/{total} sections generated!")
    print(f"{'='*60}\n")

    return generated_images


def test_api_connection() -> bool:
    """API 연결을 테스트합니다."""
    if not GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY not found")
        return False

    print(f"  API Key found: {GEMINI_API_KEY[:10]}...")

    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{"text": "Say 'API connection successful' in Korean."}]
        }]
    }

    try:
        response = requests.post(
            f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            print("  [OK] API connection successful!")
            return True
        else:
            print(f"  [FAIL] API test failed: {response.status_code}")
            return False

    except Exception as e:
        print(f"  [FAIL] API test error: {e}")
        return False


def analyze_image_style(image_path: str, output_path: str) -> Optional[str]:
    """
    이미지를 분석하여 디자인 스타일 정보를 추출합니다.

    Args:
        image_path: 분석할 이미지 파일 경로
        output_path: 결과를 저장할 마크다운 파일 경로

    Returns:
        저장된 파일 경로 또는 None (실패시)
    """
    if not GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY not found in .env")
        return None

    # 이미지 읽기 및 base64 인코딩
    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        base64_string = base64.b64encode(image_bytes).decode("utf-8")
    except Exception as e:
        print(f"  [FAIL] Failed to read image: {e}")
        return None

    # mime_type 판단
    ext = Path(image_path).suffix.lower()
    mime_type = "image/png" if ext == ".png" else "image/jpeg"

    prompt_text = """Analyze this Korean shopping mall detail page image and extract design information.
Output in structured Markdown format with these sections:

## Color Palette
- Primary, Secondary, Accent, Background colors with Hex codes

## Layout Pattern
- Section structure, spacing, alignment style

## Typography
- Headline style, body text style, font weight impression

## Visual Mood
- 3-5 keywords describing the overall mood

## Key Design Elements
- Badge/tag styles, CTA button style, card components, icon usage

## Background Pattern
- Color alternation between sections, gradient usage"""

    # 텍스트 전용 분석 모델 URL
    analysis_model = "gemini-2.0-flash"
    analysis_url = f"https://generativelanguage.googleapis.com/v1beta/models/{analysis_model}:generateContent"

    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "contents": [{
            "parts": [
                {
                    "inline_data": {
                        "mime_type": mime_type,
                        "data": base64_string
                    }
                },
                {
                    "text": prompt_text
                }
            ]
        }],
        "generationConfig": {
            "responseModalities": ["TEXT"]
        }
    }

    try:
        print(f"  Analyzing image style: {image_path}")
        response = requests.post(
            f"{analysis_url}?key={GEMINI_API_KEY}",
            headers=headers,
            json=payload,
            timeout=60
        )

        if response.status_code != 200:
            print(f"  [FAIL] API returned status {response.status_code}")
            error_text = response.text[:500]
            print(f"  Response: {error_text}")
            return None

        result = response.json()

        candidates = result.get("candidates", [])
        if not candidates:
            print("  [FAIL] No candidates in response")
            return None

        parts = candidates[0].get("content", {}).get("parts", [])
        response_text = ""
        for part in parts:
            if "text" in part:
                response_text += part["text"]

        if not response_text:
            print("  [FAIL] No text in response")
            return None

        # 마크다운 파일로 저장
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# Style Reference Analysis\n\n" + response_text)

        print(f"  [OK] Style analysis saved: {output_path}")
        return output_path

    except requests.exceptions.Timeout:
        print("  [FAIL] Request timed out (60s)")
        return None
    except requests.exceptions.RequestException as e:
        print(f"  [FAIL] Request failed - {e}")
        return None
    except Exception as e:
        print(f"  [FAIL] {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        # MD 파일에서 생성
        prompt_file = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"
        generate_all_sections_from_md(prompt_file, output_dir)
    else:
        print("Testing Gemini API connection...")
        test_api_connection()
