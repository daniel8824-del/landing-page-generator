#!/bin/bash
# landing-page-generator 스킬 설치 스크립트

set -e

SKILL_DIR="$HOME/.claude/skills/landing-page-generator"

echo "=== Landing Page Generator 스킬 설치 ==="
echo ""

# 1. 스킬 디렉토리 생성
if [ -d "$SKILL_DIR" ]; then
  echo "[!] 이미 설치되어 있습니다: $SKILL_DIR"
  read -p "    덮어쓸까요? (y/N) " answer
  if [ "$answer" != "y" ] && [ "$answer" != "Y" ]; then
    echo "    설치를 취소합니다."
    exit 0
  fi
  rm -rf "$SKILL_DIR"
fi

# 2. 파일 복사
echo "[1/4] 스킬 파일 복사 중..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$SKILL_DIR"
cp -r "$SCRIPT_DIR/SKILL.md" "$SKILL_DIR/"
cp -r "$SCRIPT_DIR/agents" "$SKILL_DIR/"
cp -r "$SCRIPT_DIR/docs" "$SKILL_DIR/"
cp -r "$SCRIPT_DIR/scripts" "$SKILL_DIR/"
cp "$SCRIPT_DIR/requirements.txt" "$SKILL_DIR/"
cp "$SCRIPT_DIR/.env.example" "$SKILL_DIR/"

# 3. Python 의존성 설치
echo "[2/4] Python 패키지 설치 중..."
pip install -r "$SKILL_DIR/requirements.txt" -q

# 4. .env 설정
echo "[3/4] API 키 설정..."
if [ ! -f "$SKILL_DIR/.env" ]; then
  cp "$SKILL_DIR/.env.example" "$SKILL_DIR/.env"
  echo ""
  echo "    ⚠️  $SKILL_DIR/.env 파일에 API 키를 설정하세요:"
  echo "    GEMINI_API_KEY=your_key_here"
  echo ""
  read -p "    API 키를 지금 입력하시겠습니까? (y/N) " setup_key
  if [ "$setup_key" = "y" ] || [ "$setup_key" = "Y" ]; then
    read -p "    GEMINI_API_KEY (필수): " gemini_key
    if [ -n "$gemini_key" ]; then
      sed -i.bak "s/your_gemini_api_key_here/$gemini_key/" "$SKILL_DIR/.env"
      rm -f "$SKILL_DIR/.env.bak"
      echo "    ✅ Gemini API 키 설정 완료"
    fi
    echo ""
    echo "    네이버 쇼핑 API (선택 — 시장 리서치 기능에 필요):"
    read -p "    NAVER_CLIENT_ID (없으면 Enter): " naver_id
    if [ -n "$naver_id" ]; then
      sed -i.bak "s/your_naver_client_id_here/$naver_id/" "$SKILL_DIR/.env"
      rm -f "$SKILL_DIR/.env.bak"
      read -p "    NAVER_CLIENT_SECRET: " naver_secret
      if [ -n "$naver_secret" ]; then
        sed -i.bak "s/your_naver_client_secret_here/$naver_secret/" "$SKILL_DIR/.env"
        rm -f "$SKILL_DIR/.env.bak"
        echo "    ✅ 네이버 API 키 설정 완료"
      fi
    else
      echo "    ⏭️  네이버 API 스킵 (시장 리서치 없이 진행 가능)"
    fi
  fi
else
  echo "    .env 파일이 이미 존재합니다."
fi

# 5. 완료
echo "[4/4] 설치 완료!"
echo ""
echo "=== 사용법 ==="
echo "Claude Code에서:"
echo "  /landing-page-generator 제품명"
echo ""
echo "예시:"
echo "  /landing-page-generator 셀 바이탈 리뉴얼 크림"
echo ""
