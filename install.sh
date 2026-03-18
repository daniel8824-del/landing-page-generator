#!/bin/bash
# Landing Page Generator - Claude Code Skill Installer

SKILL_DIR="$HOME/.claude/skills/landing-page"
INSTALL_DIR="$HOME/landing-page-app"

echo "Installing Landing Page Generator..."

# Copy to landing-page-app
if [ -d "$INSTALL_DIR" ]; then
    echo "Updating existing installation at $INSTALL_DIR"
else
    echo "Creating $INSTALL_DIR"
    mkdir -p "$INSTALL_DIR"
fi

cp -r scripts/ "$INSTALL_DIR/"
cp -r app/ "$INSTALL_DIR/"
cp -r docs/ "$INSTALL_DIR/"
cp requirements.txt "$INSTALL_DIR/"
cp .env.example "$INSTALL_DIR/"

# Install dependencies
pip install -r "$INSTALL_DIR/requirements.txt" 2>/dev/null || pip3 install -r "$INSTALL_DIR/requirements.txt" 2>/dev/null

# Register skill
mkdir -p "$SKILL_DIR"
cp SKILL.md "$SKILL_DIR/SKILL.md"

echo ""
echo "Installation complete!"
echo ""
echo "Next steps:"
echo "1. Copy .env.example to .env and set your API keys:"
echo "   cp $INSTALL_DIR/.env.example $INSTALL_DIR/.env"
echo "   # Edit .env: GEMINI_API_KEY (required), NAVER keys (optional)"
echo ""
echo "2. Use in Claude Code:"
echo "   /landing-page 셀 바이탈 리뉴얼 크림"
