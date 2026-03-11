# landing-page-generator

Claude Code skill — Enter product info, AI auto-generates a 13-section product detail page image.

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Features

- **6-Phase Pipeline** — Automated orchestration from info gathering to final image stitching
- **Gemini 3 Pro** — REST API-based photorealistic image generation (1200×~7000px)
- **Parallel Processing** — Copywriting and design run simultaneously
- **Naver Shopping API** — Auto-collect market research data (optional)
- **Reference Image** — Upload a design reference and AI analyzes the style

## Quick Start

### Install

```bash
git clone https://github.com/daniel8824-del/landing-page-generator ~/.claude/skills/landing-page-generator
cd ~/.claude/skills/landing-page-generator
bash install.sh
```

### Usage

In Claude Code:
```
/landing-page-generator 제품명
```

### Environment

Create `.env` (see `.env.example`):
```
GEMINI_API_KEY=your-api-key          # Required
NAVER_CLIENT_ID=your-id              # Optional (market research)
NAVER_CLIENT_SECRET=your-secret      # Optional (market research)
```

## 13 Sections

| # | Section | Role |
|---|---------|------|
| 01 | Hero | Headline, CTA, urgency badge |
| 02 | Pain | Customer pain points |
| 03 | Problem | Root cause, structural problem |
| 04 | Story | Before → After transformation |
| 05 | Solution | One-line product definition |
| 06 | How It Works | Step-by-step process |
| 07 | Social Proof | Reviews, statistics |
| 08 | Authority | Creator/brand introduction |
| 09 | Benefits | Perks, bonuses |
| 10 | Risk Removal | Refund policy, FAQ |
| 11 | Comparison | Before/After comparison |
| 12 | Target Filter | Recommended/not recommended |
| 13 | Final CTA | Final purchase CTA |

## Pipeline

```
Phase 1: Info Gathering (analyst)
Phase 2: Research (document-specialist) + Naver API
Phase 3: Copywriting (writer) ∥ Design (designer) — parallel
Phase 4: Prompting (executor)
Phase 5: Gemini 3 Pro image generation × 13
Phase 6: Pillow stitching → final PNG/PDF
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for full details.

## Rules

- **Width**: Exactly **1200px** (never change)
- **Style**: **Photorealistic** (no illustrations/cartoons/vectors)
- **Font**: **Pretendard Bold** (weight 700+) for all Korean text
- **Text limit**: Max **15 characters** per Korean sentence

## CLI Reference

```bash
pip install -r requirements.txt
python scripts/gemini_api.py 05-prompt.md output/       # Image generation only
python scripts/stitch_images.py output/sections          # Stitching only
python scripts/naver_search.py "product" "category" output/  # Market research only
```

## License

MIT — see [LICENSE](LICENSE).
