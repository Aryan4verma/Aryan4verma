#!/usr/bin/env python3
"""Render the Aryan4verma profile README cards.

Install FontTools, then run the script normally for animated cards. Set
STATIC=1 for the same cards at their final frame, ready for a screenshot.
Set PORTRAIT_PATH to a PNG, JPEG, or WebP file to add a portrait.
"""

from __future__ import annotations

import base64
import calendar
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from html import escape
from pathlib import Path
from typing import Any

from PIL import Image, ImageEnhance, ImageOps

ROOT = Path(__file__).resolve().parents[1]
CARDS_DIR = ROOT / "cards"
DATA_FILE = ROOT / "data" / "contributions.json"
FONT_DIR = ROOT / "assets" / "fonts"
STATIC = os.environ.get("STATIC", "").strip() == "1"
USERNAME = "Aryan4verma"
NAME = "Aryan Verma"

PAPER = "#FCFBF8"
PAPER_ALT = "#F2F5F8"
RULE = "#D6DEE8"
INK = "#0A1A31"
INK_2 = "#405675"
INK_3 = "#5C7088"
NAVY = "#071429"
ACCENT = "#9B661F"
ACCENT_LIGHT = "#D8A45E"
GRAPH_LEVELS = {
    0: PAPER_ALT,
    1: "#F4E8D6",
    2: "#E8CC9F",
    3: ACCENT_LIGHT,
    4: ACCENT,
}

TILES = [
    {
        "slug": "build",
        "label": "BUILD",
        "title": "3 featured projects",
        "detail": "PRODUCT  ·  AI  ·  VOICE",
        "url": "https://github.com/Aryan4verma?tab=repositories",
        "background": NAVY,
        "foreground": PAPER,
        "muted": "#C5D0DF",
        "accent": ACCENT_LIGHT,
    },
    {
        "slug": "applied-ai",
        "label": "APPLIED AI",
        "title": "From scan to review",
        "detail": "OCR  ·  DATA  ·  HUMAN CHECKS",
        "url": "https://github.com/Aryan4verma/AI_Land_Record",
        "background": ACCENT,
        "foreground": PAPER,
        "muted": "#F4E8D6",
        "accent": "#F8D8A8",
    },
    {
        "slug": "connect",
        "label": "CONNECT",
        "title": "Open to internships",
        "detail": "SOFTWARE  ·  AI  ·  OPEN SOURCE",
        "url": "https://www.linkedin.com/in/aryan-verma-509678346/",
        "background": PAPER_ALT,
        "foreground": INK,
        "muted": INK_2,
        "accent": ACCENT,
    },
]

PROJECTS = [
    {
        "slug": "control-engineering",
        "number": "01",
        "category": "PRODUCT SYSTEMS",
        "name": "Control Engineering",
        "description": "Industrial valve discovery, connected to product-specific customer enquiries.",
        "stack": "REACT  ·  TYPESCRIPT  ·  TANSTACK START  ·  SUPABASE",
        "repo": "https://github.com/Aryan4verma/Control-Engineering",
        "live": "https://controlengineering.co.in/",
    },
    {
        "slug": "ai-land-record",
        "number": "02",
        "category": "APPLIED AI",
        "name": "AI Land Record",
        "description": "Turn scanned land records into structured data for careful human review.",
        "stack": "PYTHON  ·  FASTAPI  ·  TESSERACT  ·  REACT",
        "repo": "https://github.com/Aryan4verma/AI_Land_Record",
        "live": "https://ai-land-record.vercel.app/",
    },
    {
        "slug": "jarvis-voice-assistant",
        "number": "03",
        "category": "VOICE INTERFACES",
        "name": "Jarvis Voice Assistant",
        "description": "A Windows-focused voice assistant with streaming chat and flexible AI providers.",
        "stack": "REACT  ·  TYPESCRIPT  ·  NODE.JS  ·  THREE.JS",
        "repo": "https://github.com/Aryan4verma/Jarvis-voice-assistant",
        "live": None,
    },
]

FONT_SOURCES = {
    "serif": ("InstrumentSerif-Regular.ttf", "Instrument Serif", "400", "normal"),
    "serif_italic": ("InstrumentSerif-Italic.ttf", "Instrument Serif", "400", "italic"),
    "sans": ("InterTight[wght].ttf", "Inter Tight", "400 700", "normal"),
    "mono": ("JetBrainsMono[wght].ttf", "JetBrains Mono", "400 700", "normal"),
}


def xml_text(value: Any) -> str:
    return escape(str(value), quote=False)


def xml_attr(value: Any) -> str:
    return escape(str(value), quote=True)


def month_sequence(today: date, count: int = 12) -> list[tuple[int, int]]:
    current = today.year * 12 + today.month - 1
    return [
        (index // 12, index % 12 + 1)
        for index in range(current - count + 1, current + 1)
    ]


def load_contributions() -> tuple[list[dict[str, Any]], date, date]:
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=364)
    by_date: dict[date, dict[str, Any]] = {}

    if DATA_FILE.exists():
        try:
            raw = json.loads(DATA_FILE.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{DATA_FILE.relative_to(ROOT)} is not valid JSON") from exc

        for item in raw.get("days", []):
            try:
                day = date.fromisoformat(str(item["date"]))
            except (KeyError, TypeError, ValueError):
                continue
            if not start <= day <= today:
                continue

            count = int(item.get("count", item.get("contributionCount", 0)) or 0)
            raw_level = item.get("level", item.get("contributionLevel", 0))
            if isinstance(raw_level, str):
                level_names = {
                    "NONE": 0,
                    "FIRST_QUARTILE": 1,
                    "SECOND_QUARTILE": 2,
                    "THIRD_QUARTILE": 3,
                    "FOURTH_QUARTILE": 4,
                }
                level = level_names.get(raw_level.upper(), 0)
            else:
                level = int(raw_level or 0)
            by_date[day] = {
                "date": day,
                "count": max(0, count),
                "level": min(4, max(0, level)),
            }

    days = [
        by_date.get(day, {"date": day, "count": 0, "level": 0})
        for day_number in range(365)
        if (day := start + timedelta(days=day_number)) <= today
    ]

    # Older snapshots may have counts but no contribution level. Derive a
    # compact five-step scale from the positive values in that year's data.
    positive = sorted(item["count"] for item in days if item["count"] > 0)
    if positive:
        for item in days:
            if item["count"] and item["level"] == 0:
                rank = sum(value <= item["count"] for value in positive) / len(positive)
                item["level"] = min(4, max(1, math.ceil(rank * 4)))
    return days, start, today


def summary_stats(days: list[dict[str, Any]], today: date) -> dict[str, Any]:
    counts = {item["date"]: item["count"] for item in days}
    active_days = sum(count > 0 for count in counts.values())
    cursor = today if counts.get(today, 0) else today - timedelta(days=1)
    streak = 0
    while counts.get(cursor, 0) > 0:
        streak += 1
        cursor -= timedelta(days=1)

    busiest = max(days, key=lambda item: (item["count"], item["date"]))
    if busiest["count"] == 0:
        busiest_label = "—"
        busiest_date = "No contributions yet"
    else:
        busiest_label = f'{busiest["date"].strftime("%a")} · {busiest["count"]}'
        busiest_date = (
            f'{calendar.month_abbr[busiest["date"].month]} {busiest["date"].day}'
        )

    monthly = defaultdict(int)
    for item in days:
        monthly[(item["date"].year, item["date"].month)] += item["count"]
    months = [
        {
            "year": year,
            "month": month,
            "label": calendar.month_abbr[month].upper(),
            "count": monthly[(year, month)],
        }
        for year, month in month_sequence(today)
    ]
    return {
        "active_days": active_days,
        "streak": streak,
        "busiest_label": busiest_label,
        "busiest_date": busiest_date,
        "total": sum(item["count"] for item in days),
        "months": months,
    }


def font_text() -> str:
    strings = [
        NAME,
        USERNAME,
        "COMPUTER SCIENCE · APPLIED AI · FULL-STACK SOFTWARE",
        "CSE student building applied AI and full-stack software.",
        "ARYANVERMA21.VERCEL.APP OPEN TO SOFTWARE AI INTERNSHIPS",
        "GITHUB ACTIVITY LAST 12 MONTHS",
        "A YEAR OF STEADY PRACTICE",
        "CURRENT STREAK ACTIVE DAYS BUSIEST DAY BEST MONTH",
        "CONTRIBUTIONS PER MONTH",
        "THE DAILY PRACTICE YOUR CONTRIBUTION GRAPH",
        "LESS MORE VIEW REPOSITORY VIEW REPO",
        "PRODUCT SYSTEMS APPLIED AI VOICE INTERFACES",
        "3 FEATURED PROJECTS FROM SCAN TO REVIEW OPEN TO INTERNSHIPS",
        "PRODUCT AI VOICE OCR DATA HUMAN CHECKS SOFTWARE OPEN SOURCE",
        "CONTROL ENGINEERING AI LAND RECORD JARVIS VOICE ASSISTANT",
        "INDUSTRIAL CATALOG SCANNED RECORDS STREAMING CHAT",
        "FROM PHOTO TO CODE VIEW LIVE SITE UPDATED CONTRIBUTIONS",
        "ARYAN VERMA",
        " .,:-=+*#%@",
    ]
    for tile in TILES:
        strings.extend([tile["label"], tile["title"], tile["detail"]])
    for project in PROJECTS:
        strings.extend(
            [
                project["number"],
                project["category"],
                project["name"],
                project["description"],
                project["stack"],
                "VIEW REPOSITORY",
            ]
        )
    strings.extend(calendar.month_abbr[month].upper() for month in range(1, 13))
    strings.extend(calendar.day_abbr)
    strings.extend(str(number) for number in range(10))
    strings.extend(["/", "·", "×", "→", "↗", "—", "&", "’", ".", ",", ":", "-", "(", ")"])
    return " ".join(strings)


def subsetter_command() -> list[str]:
    executable = shutil.which("pyftsubset")
    if executable:
        return [executable]
    try:
        import fontTools  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "FontTools is required. Install it with python -m pip install fonttools."
        ) from exc
    return [sys.executable, "-m", "fontTools.subset"]


def embedded_fonts() -> dict[str, str]:
    command = subsetter_command()
    subset_text = font_text()
    result: dict[str, str] = {}
    with tempfile.TemporaryDirectory(prefix="profile-card-fonts-") as temp_dir:
        temp = Path(temp_dir)
        for key, (filename, family, weight, font_style) in FONT_SOURCES.items():
            source = FONT_DIR / filename
            if not source.exists():
                raise FileNotFoundError(f"Font source not found: {source}")
            output = temp / f"{key}.woff"
            subprocess.run(
                [
                    *command,
                    str(source),
                    f"--output-file={output}",
                    "--flavor=woff",
                    f"--text={subset_text}",
                    "--layout-features=*",
                    "--recommended-glyphs",
                    "--no-hinting",
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            data = base64.b64encode(output.read_bytes()).decode("ascii")
            result[key] = (
                f"@font-face{{font-family:'{family}';"
                f"src:url('data:font/woff;base64,{data}') format('woff');"
                f"font-style:{font_style};font-weight:{weight};font-display:swap;}}"
            )
    return result


def style_block(fonts: dict[str, str], delay: float) -> str:
    static_rule = ""
    if STATIC:
        static_rule = (
            ".enter,.tile-enter,.portrait-row,.cell,.bar,.glint,.arrow{"
            "animation:none!important;opacity:1!important;transform:none!important}"
            ".glint{opacity:0!important}.trace{stroke-dashoffset:0!important;}"
        )
    return f"""
{fonts['serif']}
{fonts['serif_italic']}
{fonts['sans']}
{fonts['mono']}
*{{box-sizing:border-box}}
.serif{{font-family:'Instrument Serif',Georgia,serif}}
.serif-italic{{font-family:'Instrument Serif',Georgia,serif;font-style:italic}}
.sans{{font-family:'Inter Tight',Arial,sans-serif}}
.mono{{font-family:'JetBrains Mono',monospace}}
.enter{{opacity:0;transform:translateY(14px);animation:card-in .72s cubic-bezier(.22,1,.36,1) both;animation-delay:{delay:.2f}s}}
.tile-enter{{opacity:0;transform-origin:50% 50%;animation:tile-in .86s cubic-bezier(.16,1,.3,1) both;animation-delay:{delay:.2f}s}}
.portrait-row{{opacity:0;animation:portrait-print .22s linear both}}
.cell{{opacity:0;transform-box:fill-box;transform-origin:center;animation:cell-pop .28s cubic-bezier(.16,1,.3,1) both}}
.bar{{transform-box:fill-box;transform-origin:50% 100%;animation:bar-in .68s cubic-bezier(.22,1,.36,1) both}}
.glint{{opacity:.2;animation:glint-sweep 7s ease-in-out 2.2s infinite both}}
.arrow{{transform-box:fill-box;transform-origin:center;animation:arrow-nudge 2.8s ease-in-out {delay + 0.7:.2f}s infinite}}
.trace{{fill:none;stroke:{ACCENT_LIGHT};stroke-width:2.5;stroke-linecap:round;stroke-linejoin:round}}
@keyframes card-in{{to{{opacity:1;transform:translateY(0)}}}}
@keyframes tile-in{{0%{{opacity:0;transform:translateY(24px) rotate(-1.3deg) scale(.975)}}75%{{opacity:1;transform:translateY(-2px) rotate(.2deg) scale(1.006)}}100%{{opacity:1;transform:translateY(0) rotate(0) scale(1)}}}}
@keyframes portrait-print{{to{{opacity:.88}}}}
@keyframes cell-pop{{from{{opacity:0;transform:scale(.38)}}to{{opacity:1;transform:scale(1)}}}}
@keyframes bar-in{{from{{opacity:.35;transform:scaleY(.04)}}to{{opacity:1;transform:scaleY(1)}}}}
@keyframes glint-sweep{{0%,72%,100%{{transform:translateX(-360px)}}84%{{transform:translateX(360px)}}}}
@keyframes arrow-nudge{{0%,72%,100%{{transform:translateX(0)}}82%{{transform:translateX(4px)}}}}
@media (prefers-reduced-motion:reduce){{
  .enter,.tile-enter,.portrait-row,.cell,.bar,.glint,.arrow{{animation:none!important;opacity:1!important;transform:none!important}}
  .glint{{opacity:0!important}}
  .trace{{stroke-dashoffset:0!important}}
}}
{static_rule}
"""


def svg_document(
    width: int,
    height: int,
    title: str,
    description: str,
    body: str,
    fonts: dict[str, str],
    delay: float,
) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title description">
<title id="title">{xml_text(title)}</title>
<desc id="description">{xml_text(description)}</desc>
<style>{style_block(fonts, delay)}</style>
{body}
</svg>
'''


def card_background(width: int, height: int) -> str:
    return (
        f'<rect width="{width}" height="{height}" rx="16" fill="{PAPER}"/>'
        f'<rect x="1" y="1" width="{width - 2}" height="{height - 2}" '
        f'rx="15" fill="none" stroke="{RULE}" stroke-width="2"/>'
    )


def portrait_element() -> str:
    portrait = os.environ.get("PORTRAIT_PATH", "").strip()
    path = Path(portrait) if portrait else ROOT / "assets" / "portrait.jpg"
    if not path.is_absolute():
        path = ROOT / path
    if not path.is_file():
        raise FileNotFoundError(f"Portrait file not found: {path}")
    width, height = 100, 72
    image = Image.open(path).convert("L")
    image = ImageOps.fit(
        image,
        (width, height),
        method=Image.Resampling.LANCZOS,
        centering=(0.5, 0.12),
    )
    image = ImageEnhance.Contrast(ImageOps.autocontrast(image)).enhance(1.15)
    ramp = " .,:-=+*#%@"
    rows = []
    for row_index in range(height):
        chars = []
        for pixel in range(width):
            luminance = image.getpixel((pixel, row_index))
            shade = round((255 - luminance) / 255 * (len(ramp) - 1))
            chars.append(ramp[shade])
        baseline = 49 + row_index * 4.15
        row_delay = 0.28 + row_index * 0.014
        rows.append(
            f'<text class="portrait-row mono" style="animation-delay:{row_delay:.3f}s" '
            f'xml:space="preserve" x="710" y="{baseline:.2f}" '
            f'fill="{INK}" font-size="4.4">'
            f'{xml_text("".join(chars))}</text>'
        )
    return f'''
<rect x="697" y="22" width="282" height="332" rx="14" fill="{PAPER_ALT}"/>
<rect x="697.5" y="22.5" width="281" height="331" rx="13.5" fill="none" stroke="{RULE}"/>
<g aria-label="ASCII portrait generated from Aryan's GitHub profile photo">
  {''.join(rows)}
</g>
<path d="M710 368h34" stroke="{ACCENT}" stroke-width="2.5"/>
<text x="753" y="372" class="mono" fill="{INK_3}" font-size="11" letter-spacing="1.2">FROM PHOTO · TO CODE</text>
'''


def render_hero(fonts: dict[str, str]) -> str:
    portrait = portrait_element()
    body = f'''
{card_background(1000, 390)}
<path d="M70 42h54" stroke="{ACCENT}" stroke-width="3"/>
<g class="enter">
  <text x="70" y="70" class="mono" fill="{INK_3}" font-size="14" letter-spacing="2.1">CSE  ·  APPLIED AI  ·  FULL-STACK SOFTWARE</text>
  <text x="65" y="158" class="serif" fill="{INK}" font-size="86" letter-spacing="-1.3">Aryan</text>
  <text x="62" y="239" class="serif-italic" fill="{INK}" font-size="96" letter-spacing="-1.8">Verma</text>
  <text x="70" y="282" class="sans" fill="{INK_2}" font-size="20">CSE student building applied AI and full-stack software.</text>
  <path d="M70 306h510" stroke="{RULE}" stroke-width="1"/>
  <text x="70" y="334" class="mono" fill="{INK_3}" font-size="12" letter-spacing=".45">ARYANVERMA21.VERCEL.APP  /  OPEN TO SOFTWARE &amp; AI INTERNSHIPS</text>
</g>
<defs>
  <clipPath id="verma-clip">
    <text x="62" y="239" class="serif-italic" font-size="96" letter-spacing="-1.8">Verma</text>
  </clipPath>
</defs>
<rect class="glint" x="85" y="154" width="64" height="98" fill="{ACCENT_LIGHT}" clip-path="url(#verma-clip)"/>
{portrait}
'''
    return svg_document(
        1000,
        390,
        f"{NAME} — computer science, applied AI, and full-stack software",
        "Aryan Verma with an animated ASCII portrait generated from his GitHub profile photo. CSE student building applied AI and full-stack software.",
        body,
        fonts,
        0.0,
    )


def render_tile(tile: dict[str, str], fonts: dict[str, str], delay: float) -> str:
    body = f'''
<defs><clipPath id="tile-clip"><rect width="360" height="150" rx="16"/></clipPath></defs>
<rect width="360" height="150" rx="16" fill="{tile["background"]}"/>
<rect x="1" y="1" width="358" height="148" rx="15" fill="none" stroke="{tile["accent"]}" stroke-opacity=".42"/>
<g class="tile-enter" clip-path="url(#tile-clip)">
  <path d="M0 0h5v150H0z" fill="{tile["accent"]}"/>
  <text x="25" y="35" class="mono" fill="{tile["accent"]}" font-size="12" letter-spacing="1.8">{xml_text(tile["label"])}</text>
  <text x="24" y="82" class="serif" fill="{tile["foreground"]}" font-size="28">{xml_text(tile["title"])}</text>
  <text x="25" y="119" class="mono" fill="{tile["muted"]}" font-size="10.5" letter-spacing=".75">{xml_text(tile["detail"])}</text>
  <path class="arrow" d="M322 32h13m-5-5 5 5-5 5" fill="none" stroke="{tile["accent"]}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
  <path class="glint" d="M-30 150 22 0h24L-6 150z" fill="{PAPER}" opacity=".22"/>
</g>
'''
    return svg_document(
        360,
        150,
        tile["title"],
        tile["detail"],
        body,
        fonts,
        delay,
    )


def render_contributions(
    days: list[dict[str, Any]],
    stats: dict[str, Any],
    updated: str,
    fonts: dict[str, str],
    delay: float,
) -> str:
    width, height = 1000, 444
    chart_x, chart_width = 72, 856
    baseline, chart_height = 370, 82
    bar_width = 42
    gap = (chart_width - 12 * bar_width) / 11
    max_value = max((month["count"] for month in stats["months"]), default=0) or 1
    best_count = max((month["count"] for month in stats["months"]), default=0)
    best_month = next(
        (month for month in stats["months"] if month["count"] == best_count and best_count),
        None,
    )
    bars: list[str] = []
    values: list[str] = []
    points: list[tuple[float, float]] = []

    for index, month in enumerate(stats["months"]):
        x = chart_x + index * (bar_width + gap)
        value = month["count"]
        bar_height = max(3, chart_height * value / max_value) if value else 2
        y = baseline - bar_height
        fill = "#F8D8A8" if best_count and value == best_count else ACCENT_LIGHT
        if value == 0:
            fill = "#31445C"
        bar_delay = delay + 0.24 + index * 0.038
        bars.append(
            f'<rect class="bar" style="animation-delay:{bar_delay:.2f}s" '
            f'x="{x:.1f}" y="{y:.1f}" width="{bar_width}" height="{bar_height:.1f}" '
            f'rx="5" fill="{fill}"><title>{xml_text(month["label"].title())} '
            f'{month["year"]}: {value} contributions</title></rect>'
        )
        if value:
            values.append(
                f'<text x="{x + bar_width / 2:.1f}" y="{max(285, y - 8):.1f}" '
                f'text-anchor="middle" class="mono" fill="#EAF0F9" font-size="11">{value}</text>'
            )
        points.append((x + bar_width / 2, y - 4))

    path_data = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in points)
    path_length = sum(
        math.hypot(
            points[index][0] - points[index - 1][0],
            points[index][1] - points[index - 1][1],
        )
        for index in range(1, len(points))
    )
    if STATIC:
        trace = (
            f'<path class="trace" d="{path_data}" stroke="{ACCENT_LIGHT}" '
            f'stroke-dasharray="{path_length:.1f}" stroke-dashoffset="0"/>'
        )
    else:
        trace = (
            f'<path class="trace" d="{path_data}" stroke="{ACCENT_LIGHT}" '
            f'stroke-dasharray="{path_length:.1f}" stroke-dashoffset="{path_length:.1f}">'
            f'<animate attributeName="stroke-dashoffset" values="{path_length:.1f};0" '
            f'dur="1.15s" begin="{delay + 0.3:.2f}s" fill="freeze"/>'
            "</path>"
        )

    busiest_value = stats["busiest_label"]
    total_note = f'{stats["total"]:,} CONTRIBUTIONS · UPDATED {updated}'
    month_labels = "".join(
        f'<text x="{chart_x + i * (bar_width + gap) + bar_width / 2:.1f}" y="407" '
        f'text-anchor="middle" class="mono" fill="#A8BAD4" font-size="11.5">{month["label"]}</text>'
        for i, month in enumerate(stats["months"])
    )
    best_note = (
        f'{best_month["label"]} · {best_month["count"]} contributions'
        if best_month
        else "No contributions in this window"
    )
    body = f'''
<rect width="{width}" height="{height}" rx="16" fill="{NAVY}"/>
<rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="15" fill="none" stroke="#1C3357" stroke-width="2"/>
<g class="enter">
  <text x="58" y="51" class="mono" fill="{ACCENT_LIGHT}" font-size="13" letter-spacing="1.8">GITHUB ACTIVITY  /  LAST 12 MONTHS</text>
  <text x="58" y="103" class="serif" fill="{PAPER}" font-size="47">A year of steady practice.</text>
  <text x="942" y="52" text-anchor="end" class="mono" fill="#A8BAD4" font-size="12" letter-spacing=".35">{xml_text(total_note)}</text>
  <path d="M58 122h884" stroke="#1C3357" stroke-width="1.5"/>
  <text x="68" y="154" class="mono" fill="#A8BAD4" font-size="11.5" letter-spacing="1">CURRENT STREAK</text>
  <text x="68" y="200" class="serif" fill="{PAPER}" font-size="37">{stats["streak"]} day{"s" if stats["streak"] != 1 else ""}</text>
  <text x="68" y="222" class="sans" fill="#A8BAD4" font-size="13">consecutive active days</text>
  <path d="M341 141v89M624 141v89" stroke="#1C3357" stroke-width="1.5"/>
  <text x="371" y="154" class="mono" fill="#A8BAD4" font-size="11.5" letter-spacing="1">ACTIVE DAYS</text>
  <text x="371" y="200" class="serif" fill="{PAPER}" font-size="37">{stats["active_days"]} days</text>
  <text x="371" y="222" class="sans" fill="#A8BAD4" font-size="13">of the last year</text>
  <text x="654" y="154" class="mono" fill="#A8BAD4" font-size="11.5" letter-spacing="1">BUSIEST DAY</text>
  <text x="654" y="200" class="serif" fill="{PAPER}" font-size="37">{xml_text(busiest_value)}</text>
  <text x="654" y="222" class="sans" fill="#A8BAD4" font-size="13">{xml_text(stats["busiest_date"])} · contributions</text>
  <text x="64" y="266" class="mono" fill="#A8BAD4" font-size="11.5" letter-spacing=".9">CONTRIBUTIONS PER MONTH</text>
  <text x="936" y="266" text-anchor="end" class="mono" fill="{ACCENT_LIGHT}" font-size="11.5" letter-spacing=".35">BEST  ·  {xml_text(best_note.upper())}</text>
  <path d="M64 {baseline}h872" stroke="#31445C" stroke-width="1.5"/>
  {''.join(bars)}
  {''.join(values)}
  {trace}
  {month_labels}
</g>
'''
    return svg_document(
        width,
        height,
        "GitHub contributions over the last 12 months",
        f'{stats["total"]} contributions, {stats["active_days"]} active days, '
        f'{stats["streak"]} day streak, busiest day {stats["busiest_date"]}. '
        f"Updated {updated}. Best month: {best_note}.",
        body,
        fonts,
        delay,
    )


def render_project(
    project: dict[str, Any], fonts: dict[str, str], delay: float
) -> str:
    width, height = 1000, 250
    visuals = project_illustration(project)
    body = f'''
{card_background(width, height)}
<g class="enter">
  <text x="62" y="49" class="mono" fill="{ACCENT}" font-size="12.5" letter-spacing="1.8">{project["number"]}  /  {xml_text(project["category"])}</text>
  <text x="60" y="112" class="serif" fill="{INK}" font-size="51" letter-spacing="-.5">{xml_text(project["name"])}</text>
  <text x="64" y="154" class="sans" fill="{INK_2}" font-size="17.5">{xml_text(project["description"])}</text>
  <text x="64" y="198" class="mono" fill="{INK_3}" font-size="11.5" letter-spacing=".3">{xml_text(project["stack"])}</text>
  <path d="M64 218h640" stroke="{RULE}" stroke-width="1"/>
  <text x="64" y="237" class="mono" fill="{INK_3}" font-size="10.5" letter-spacing=".8">VIEW REPOSITORY  ↗</text>
  {visuals}
</g>
'''
    return svg_document(
        width,
        height,
        project["name"],
        f'{project["description"]} Technologies: {project["stack"]}.',
        body,
        fonts,
        delay,
    )


def project_illustration(project: dict[str, Any]) -> str:
    """Draw a small, project-specific line illustration in the card margin."""
    slug = project["slug"]
    if slug == "control-engineering":
        art = f'''
<g fill="none" stroke="{ACCENT}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M783 92h42m62 0h45M783 151h42m62 0h45M783 92v59m149-59v59"/>
  <path d="m825 76 31 16-31 16zm62 0-31 16 31 16zm-31 40v18m-8 0h16"/>
  <circle cx="856" cy="151" r="18" fill="{PAPER_ALT}"/><path d="M856 141v10l7 5"/>
  <path d="M795 73v-9h30m62 95v9h30" stroke="{RULE}"/>
</g>
<text x="856" y="208" text-anchor="middle" class="mono" fill="{INK_3}" font-size="9.5" letter-spacing="1">FLOW / CONTROL</text>'''
    elif slug == "ai-land-record":
        art = f'''
<g fill="none" stroke="{RULE}" stroke-width="1.5" stroke-linejoin="round">
  <path d="M817 56h69l26 26v113h-95z" fill="{PAPER_ALT}"/>
  <path d="M886 56v27h26M832 99h63M832 113h48M832 127h58M832 141h37M832 158h63"/>
</g>
<g fill="none" stroke="{ACCENT}" stroke-width="2">
  <path d="M826 94h26v25h-26zm41 33h28v24h-28zM826 151h22v16h-22z"/>
  <path d="M814 73v-9h9m86 9v-9h-9m-86 104v9h9m86-9v9h-9" stroke-width="1.5"/>
</g>
<text x="856" y="218" text-anchor="middle" class="mono" fill="{INK_3}" font-size="9.5" letter-spacing="1">SCAN / STRUCTURE</text>'''
    else:
        bars = [8, 15, 23, 12, 31, 18, 26, 11, 34, 16, 24, 9, 29, 14, 21, 10]
        wave = " ".join(
            f"M{790 + i * 9} {122 - height / 2:.1f}v{height}"
            for i, height in enumerate(bars)
        )
        art = f'''
<circle cx="857" cy="121" r="66" fill="{PAPER_ALT}" stroke="{RULE}" stroke-width="1.5"/>
<circle cx="857" cy="121" r="49" fill="none" stroke="{RULE}" stroke-width="1" stroke-dasharray="2 5"/>
<circle cx="857" cy="121" r="30" fill="{PAPER}" stroke="{ACCENT}" stroke-width="1.5"/>
<path d="{wave}" fill="none" stroke="{ACCENT}" stroke-width="2.2" stroke-linecap="round"/>
<text x="857" y="213" text-anchor="middle" class="mono" fill="{INK_3}" font-size="9.5" letter-spacing="1">LISTEN / RESPOND</text>'''
    return f'<g aria-hidden="true">{art}</g>'


def render_graph(
    days: list[dict[str, Any]],
    stats: dict[str, Any],
    updated: str,
    fonts: dict[str, str],
    delay: float,
) -> str:
    width, height = 1000, 326
    by_date = {item["date"]: item for item in days}
    start_sunday = days[0]["date"] - timedelta(days=(days[0]["date"].weekday() + 1) % 7)
    columns = 53
    cell = 11
    gap = 4
    grid_x, grid_y = 104, 151
    grid_width = columns * (cell + gap) - gap
    cells: list[str] = []

    for column in range(columns):
        for row in range(7):
            day = start_sunday + timedelta(days=column * 7 + row)
            item = by_date.get(day)
            count = item["count"] if item else 0
            level = item["level"] if item else 0
            color = GRAPH_LEVELS.get(level, ACCENT)
            if count > 0 and level == 0:
                color = GRAPH_LEVELS[1]
            x = grid_x + column * (cell + gap)
            y = grid_y + row * (cell + gap)
            cell_delay = delay + 0.10 + column * 0.008 + row * 0.001
            cells.append(
                f'<rect class="cell" style="animation-delay:{cell_delay:.3f}s" '
                f'x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2.2" '
                f'fill="{color}"><title>{day.isoformat()}: {count} '
                f'contribution{"s" if count != 1 else ""}</title></rect>'
            )

    month_labels: list[str] = []
    previous_month = None
    for column in range(columns):
        week_start = start_sunday + timedelta(days=column * 7)
        month_key = (week_start.year, week_start.month)
        if month_key != previous_month:
            month_labels.append(
                f'<text x="{grid_x + column * (cell + gap)}" y="137" class="mono" '
                f'fill="{INK_3}" font-size="12">{calendar.month_abbr[week_start.month].upper()}</text>'
            )
            previous_month = month_key

    day_labels = "".join(
        f'<text x="82" y="{grid_y + row * (cell + gap) + 9}" text-anchor="end" '
        f'class="mono" fill="{INK_3}" font-size="10">{label}</text>'
        for row, label in enumerate(["S", "", "T", "", "T", "", "S"])
    )
    legend_x = grid_x + grid_width - 138
    legend = [
        f'<text x="{legend_x - 37}" y="294" class="sans" fill="{INK_3}" font-size="12">Less</text>'
    ]
    for index, level in enumerate(range(5)):
        legend.append(
            f'<rect x="{legend_x + index * 19}" y="283" width="12" height="12" '
            f'rx="2.2" fill="{GRAPH_LEVELS[level]}"/>'
        )
    legend.append(
        f'<text x="{legend_x + 5 * 19 + 3}" y="294" class="sans" fill="{INK_3}" font-size="12">More</text>'
    )
    note = f'{stats["total"]:,} CONTRIBUTIONS · UPDATED {updated}'
    body = f'''
{card_background(width, height)}
<g class="enter">
  <text x="58" y="54" class="mono" fill="{ACCENT}" font-size="14" letter-spacing="1.7">THE DAILY PRACTICE</text>
  <text x="58" y="101" class="serif" fill="{INK}" font-size="44">Your contribution graph</text>
  <text x="942" y="54" text-anchor="end" class="mono" fill="{INK_3}" font-size="12.5" letter-spacing=".25">{xml_text(note)}</text>
  {''.join(month_labels)}
  {day_labels}
  {''.join(cells)}
  {''.join(legend)}
</g>
'''
    return svg_document(
        width,
        height,
        "GitHub contribution graph",
        f"Contribution graph in Aryan Verma’s ochre brand color. "
        f'{stats["total"]} contributions over the last year, updated {updated}.',
        body,
        fonts,
        delay,
    )


def write_card(filename: str, svg: str) -> None:
    CARDS_DIR.mkdir(parents=True, exist_ok=True)
    (CARDS_DIR / filename).write_text(svg, encoding="utf-8", newline="\n")


def main() -> None:
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Contribution data not found: {DATA_FILE.relative_to(ROOT)}"
        )
    days, _start, today = load_contributions()
    stats = summary_stats(days, today)
    raw = json.loads(DATA_FILE.read_text(encoding="utf-8-sig"))
    updated = str(raw.get("updated_at", raw.get("updatedAt", today.isoformat())))
    updated = updated[:10]
    fonts = embedded_fonts()

    write_card("hero.svg", render_hero(fonts))
    write_card(
        "contribution-graph.svg",
        render_graph(days, stats, updated, fonts, 1.55),
    )
    write_card(
        "contributions.svg",
        render_contributions(days, stats, updated, fonts, 2.35),
    )
    for index, tile in enumerate(TILES):
        write_card(
            f'tile-{tile["slug"]}.svg',
            render_tile(tile, fonts, 3.18 + index * 0.18),
        )
    for index, project in enumerate(PROJECTS):
        write_card(
            f'project-{project["slug"]}.svg',
            render_project(project, fonts, 4.12 + index * 0.30),
        )
    mode = "static final frame" if STATIC else "animated"
    print(f"Rendered 9 {mode} SVG cards into {CARDS_DIR.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
