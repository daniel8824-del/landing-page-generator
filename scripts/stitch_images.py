"""
섹션별 PNG 이미지를 세로로 이어붙여 최종 상세페이지를 생성하는 모듈

⚠️ 중요: 모든 이미지는 1200px 너비로 자동 리사이즈됩니다.
   Gemini API가 정확한 픽셀 크기를 보장하지 않기 때문에
   스티칭 전 강제로 1200px로 맞춥니다.

docs/stitch_images.py 참조 기반
"""

import os
import sys
from pathlib import Path
from typing import List, Optional, Tuple
from PIL import Image


# 고정 너비 (절대 변경 금지)
FIXED_WIDTH = 1200

# 기본 섹션 순서
DEFAULT_SECTION_ORDER = [
    "01_hero.png",
    "02_pain.png",
    "03_problem.png",
    "04_story.png",
    "05_solution.png",
    "06_how_it_works.png",
    "07_social_proof.png",
    "08_authority.png",
    "09_benefits.png",
    "10_risk_removal.png",
    "11_comparison.png",
    "12_target_filter.png",
    "13_final_cta.png",
]


def load_images(image_paths: List[str], target_width: int = FIXED_WIDTH) -> List[Image.Image]:
    """
    이미지 파일들을 로드하고 지정된 너비로 리사이즈합니다.

    ⚠️ 모든 이미지는 target_width로 강제 리사이즈됩니다.
    Gemini API가 정확한 픽셀 크기를 생성하지 않기 때문입니다.
    """
    images = []
    for path in image_paths:
        if os.path.exists(path):
            img = Image.open(path)
            original_size = f"{img.width}x{img.height}"

            # RGBA로 변환 (투명도 지원)
            if img.mode != 'RGBA':
                img = img.convert('RGBA')

            # 너비가 target_width와 다르면 리사이즈
            if img.width != target_width:
                ratio = target_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((target_width, new_height), Image.Resampling.LANCZOS)
                print(f"  Loaded & Resized: {path} ({original_size} → {img.width}x{img.height})")
            else:
                print(f"  Loaded: {path} ({img.width}x{img.height})")

            images.append(img)
        else:
            print(f"  [WARN] Missing: {path}")
    return images


def stitch_sections(
    image_paths: List[str],
    output_path: str,
    background_color: Tuple[int, int, int, int] = (255, 255, 255, 255),
    target_width: int = FIXED_WIDTH
) -> Optional[str]:
    """
    섹션별 PNG를 세로로 이어붙여 최종 상세페이지를 생성합니다.

    ⚠️ 모든 이미지는 target_width(기본 1200px)로 강제 리사이즈됩니다.
    """
    images = load_images(image_paths, target_width)

    if not images:
        print("  [FAIL] No images to stitch")
        return None

    # 전체 크기 계산
    total_height = sum(img.height for img in images)
    final_width = target_width

    print(f"\n  [STITCH] Stitching {len(images)} images...")
    print(f"  [SIZE] Final size: {final_width}x{total_height} (width fixed to {target_width}px)")

    # 새 캔버스 생성
    result = Image.new('RGBA', (final_width, total_height), background_color)

    # 이미지 이어붙이기
    y_offset = 0
    for i, img in enumerate(images):
        result.paste(img, (0, y_offset), img if img.mode == 'RGBA' else None)
        print(f"  [OK] Section {i+1:02d}: y={y_offset}, height={img.height}")
        y_offset += img.height

    # 출력 디렉토리 생성
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # 저장
    if output_path.lower().endswith('.pdf'):
        rgb_result = result.convert('RGB')
        rgb_result.save(output_path, 'PDF', resolution=150)
        size_mb = Path(output_path).stat().st_size / (1024 * 1024)
        print(f"\n  [SAVED] PDF saved: {output_path} ({size_mb:.1f} MB)")
    else:
        result.save(output_path, 'PNG', optimize=True)
        size_mb = Path(output_path).stat().st_size / (1024 * 1024)
        print(f"\n  [SAVED] PNG saved: {output_path} ({size_mb:.1f} MB)")

    # 메모리 해제
    for img in images:
        img.close()
    result.close()

    return output_path


def stitch_from_directory(
    input_dir: str,
    output_path: str,
    section_order: Optional[List[str]] = None
) -> Optional[str]:
    """
    디렉토리 내의 섹션 이미지들을 순서대로 이어붙입니다.
    """
    if section_order is None:
        section_order = DEFAULT_SECTION_ORDER

    image_paths = [os.path.join(input_dir, filename) for filename in section_order]

    # 존재하는 파일만 필터링
    existing_paths = [p for p in image_paths if os.path.exists(p)]

    if not existing_paths:
        # 디렉토리 내 PNG 파일 자동 탐색 (section_ 패턴도 지원)
        print(f"  Searching for PNG files in {input_dir}...")
        png_files = sorted([f for f in os.listdir(input_dir)
                           if f.endswith('.png') and not f.startswith('final')])
        existing_paths = [os.path.join(input_dir, f) for f in png_files]

    if not existing_paths:
        print(f"  [FAIL] No PNG files found in {input_dir}")
        return None

    print(f"\n{'='*60}")
    print(f"  [STITCH] Stitching {len(existing_paths)} section images")
    print(f"{'='*60}")

    return stitch_sections(existing_paths, output_path)


def stitch_all(output_dir: str) -> Optional[str]:
    """
    orchestrator.py에서 호출하는 편의 함수.
    output_dir/sections/ 내의 섹션 이미지들을 합성하여 output_dir에 저장합니다.
    """
    sections_dir = os.path.join(output_dir, "sections")

    # sections/ 폴더가 없으면 output_dir 자체에서 탐색 (하위호환)
    if not os.path.isdir(sections_dir):
        sections_dir = output_dir

    png_path = os.path.join(output_dir, "final_detail_page.png")
    pdf_path = os.path.join(output_dir, "final_detail_page.pdf")

    # PNG 생성
    result = stitch_from_directory(sections_dir, png_path)

    if result:
        # PDF도 생성
        stitch_from_directory(sections_dir, pdf_path)

        # 미리보기 생성
        preview_path = os.path.join(output_dir, "preview.png")
        create_preview(png_path, preview_path, max_height=2000)

    return result


def create_preview(
    image_path: str,
    preview_path: str,
    max_height: int = 2000
) -> Optional[str]:
    """미리보기용 축소 이미지를 생성합니다."""
    if not os.path.exists(image_path):
        print(f"  Error: File not found - {image_path}")
        return None

    img = Image.open(image_path)

    if img.height > max_height:
        ratio = max_height / img.height
        new_width = int(img.width * ratio)
        img = img.resize((new_width, max_height), Image.Resampling.LANCZOS)

    Path(preview_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(preview_path, 'PNG', optimize=True)

    print(f"  [OK] Preview saved: {preview_path} ({img.width}x{img.height})")
    img.close()
    return preview_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python stitch_images.py <input_dir> [output_path]")
        print("Example: python stitch_images.py output/sections output/final_page.png")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(input_dir, "final_detail_page.png")

    result = stitch_from_directory(input_dir, output_path)

    if result:
        print(f"\n  Success! Final page: {result}")
    else:
        print("\n  Failed to create final page")
        sys.exit(1)
