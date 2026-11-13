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
import mimetypes
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
        "slug": "portfolio",
        "label": "PORTFOLIO",
        "title": "Explore the work",
        "detail": "Builds, experiments & notes",
        "url": "https://aryanverma21.vercel.app/",
    },
    {
        "slug": "linkedin",
        "label": "LINKEDIN",
        "title": "Let’s connect",
        "detail": "Professional updates & ideas",
        "url": "https://www.linkedin.com/in/aryan-verma-509678346/",
    },
    {
        "slug": "email",
        "label": "EMAIL",
        "title": "Start a conversation",
        "detail": "Software, AI & collaboration",
        "url": "mailto:verma4aryan4@gmail.com",
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
    "serif": ("InstrumentSerif-Regular.ttf", "Instrument Serif", "400"),
    "sans": ("InterTight[wght].ttf", "Inter Tight", "400 700"),
    "mono": ("JetBrainsMono[wght].ttf", "JetBrains Mono", "400 700"),
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
        "CSE · APPLIED AI · FULL-STACK SOFTWARE",
        "CSE student building applied AI and thoughtful full-stack software.",
        "BUILDING ACROSS DATA, SOFTWARE & HUMAN INTERACTION",
        "PORTFOLIO LINKEDIN EMAIL EXPLORE THE WORK LET’S CONNECT START A CONVERSATION",
        "BUILDS, EXPERIMENTS & NOTES PROFESSIONAL UPDATES & IDEAS SOFTWARE, AI & COLLABORATION",
        "GITHUB ACTIVITY LAST 12 MONTHS A YEAR, ONE DAY AT A TIME.",
        "CURRENT STREAK ACTIVE DAYS BUSIEST DAY MONTHLY CONTRIBUTIONS CONTRIBUTIONS",
        "OF THE LAST YEAR CURRENT STREAK DAYS",
        "THE DAILY PRACTICE YOUR CONTRIBUTION GRAPH UPDATED",
        "LESS MORE",
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
    strings.extend(["/", "·", "×", "→", "↗", "—", "&", "’", ".", ",", ":", "-"])
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
        for key, (filename, family, weight) in FONT_SOURCES.items():
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
                f"font-style:normal;font-weight:{weight};font-display:swap;}}"
            )
    return result


def style_block(fonts: dict[str, str], delay: float) -> str:
    static_rule = ""
    if STATIC:
        static_rule = (
            ".enter,.bar{animation:none!important;opacity:1!important;"
            "transform:none!important}.trace{stroke-dashoffset:0!important;}"
        )
    return f"""
{fonts['serif']}
{fonts['sans']}
{fonts['mono']}
*{{box-sizing:border-box}}
.serif{{font-family:'Instrument Serif',Georgia,serif}}
.sans{{font-family:'Inter Tight',Arial,sans-serif}}
.mono{{font-family:'JetBrains Mono',monospace}}
.enter{{opacity:0;transform:translateY(14px);animation:card-in .72s cubic-bezier(.22,1,.36,1) both;animation-delay:{delay:.2f}s}}
.bar{{transform-box:fill-box;transform-origin:50% 100%;animation:bar-in .72s cubic-bezier(.22,1,.36,1) both}}
.trace{{fill:none;stroke:{ACCENT_LIGHT};stroke-width:2.5;stroke-linecap:round;stroke-linejoin:round}}
@keyframes card-in{{to{{opacity:1;transform:translateY(0)}}}}
@keyframes bar-in{{from{{opacity:.35;transform:scaleY(.04)}}to{{opacity:1;transform:scaleY(1)}}}}
@media (prefers-reduced-motion:reduce){{
  .enter,.bar{{animation:none!important;opacity:1!important;transform:none!important}}
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
        f'<rect width="{width}" height="{height}" rx="20" fill="{PAPER}"/>'
        f'<rect x="1" y="1" width="{width - 2}" height="{height - 2}" '
        f'rx="19" fill="none" stroke="{RULE}" stroke-width="2"/>'
    )


def portrait_element() -> str:
    portrait = os.environ.get("PORTRAIT_PATH", "").strip()
    if not portrait:
        return ""
    path = Path(portrait)
    if not path.is_absolute():
        path = ROOT / path
    if not path.is_file():
        raise FileNotFoundError(f"Portrait file not found: {path}")
    mime = mimetypes.guess_type(path.name)[0]
    if mime not in {"image/png", "image/jpeg", "image/webp"}:
        raise ValueError("PORTRAIT_PATH must point to a PNG, JPEG, or WebP image.")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f'''
<defs><clipPath id="portrait-clip"><rect x="810" y="48" width="132" height="204" rx="16"/></clipPath></defs>
<image href="data:{mime};base64,{encoded}" x="810" y="48" width="132" height="204" preserveAspectRatio="xMidYMid slice" clip-path="url(#portrait-clip)"/>
<rect x="810" y="48" width="132" height="204" rx="16" fill="none" stroke="{RULE}" stroke-width="2"/>
'''


def render_hero(fonts: dict[str, str]) -> str:
    portrait = portrait_element()
    if portrait:
        motif = f'<g class="enter">{portrait}</g>'
    else:
        motif = f'''
<g aria-hidden="true">
  <circle cx="864" cy="150" r="99" fill="{PAPER_ALT}"/>
  <circle cx="864" cy="150" r="72" fill="none" stroke="{RULE}" stroke-width="1.5"/>
  <circle cx="864" cy="150" r="48" fill="none" stroke="{ACCENT_LIGHT}" stroke-width="2"/>
  <path d="M774 150h180M864 60v180" stroke="{RULE}" stroke-width="1"/>
  <circle cx="864" cy="150" r="9" fill="{ACCENT}"/>
  <circle cx="914" cy="103" r="5" fill="{ACCENT_LIGHT}"/>
  <rect x="790" y="235" width="148" height="28" rx="14" fill="{PAPER}" stroke="{RULE}"/>
  <text x="864" y="254" text-anchor="middle" class="mono" fill="{INK_2}" font-size="12" letter-spacing="1.2">DATA / SOFTWARE / PEOPLE</text>
</g>
'''
    body = f'''
{card_background(1000, 300)}
<path d="M70 50h54" stroke="{ACCENT}" stroke-width="3"/>
<g class="enter">
  <text x="70" y="80" class="mono" fill="{INK_3}" font-size="15" letter-spacing="2.2">CSE  ·  APPLIED AI  ·  FULL-STACK SOFTWARE</text>
  <text x="65" y="166" class="serif" fill="{INK}" font-size="90" letter-spacing="-1.3">{xml_text(NAME)}</text>
  <text x="72" y="216" class="sans" fill="{INK_2}" font-size="22">CSE student building applied AI and thoughtful full-stack software.</text>
  <text x="72" y="263" class="mono" fill="{INK_3}" font-size="13" letter-spacing=".65">BUILDING ACROSS DATA, SOFTWARE &amp; HUMAN INTERACTION</text>
  <circle cx="73" cy="285" r="3.5" fill="{ACCENT}"/>
  <text x="86" y="290" class="mono" fill="{INK_3}" font-size="12" letter-spacing=".5">@{USERNAME}</text>
</g>
{motif}
'''
    return svg_document(
        1000,
        300,
        f"{NAME} — applied AI and full-stack software",
        "Computer science student building applied AI and thoughtful full-stack software.",
        body,
        fonts,
        0.0,
    )


def render_tile(tile: dict[str, str], fonts: dict[str, str], delay: float) -> str:
    body = f'''
{card_background(360, 138)}
<g class="enter">
  <text x="25" y="34" class="mono" fill="{ACCENT}" font-size="12" letter-spacing="1.5">{xml_text(tile["label"])}</text>
  <text x="24" y="76" class="serif" fill="{INK}" font-size="29">{xml_text(tile["title"])}</text>
  <text x="25" y="111" class="sans" fill="{INK_2}" font-size="13.5">{xml_text(tile["detail"])}</text>
  <circle cx="321" cy="70" r="18" fill="{PAPER_ALT}" stroke="{RULE}"/>
  <path d="M313 70h15m-6-6 6 6-6 6" fill="none" stroke="{ACCENT}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
</g>
'''
    return svg_document(
        360,
        138,
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
    width, height = 1000, 425
    chart_x, chart_width = 74, 852
    baseline, chart_height = 355, 94
    bar_width = 42
    gap = (chart_width - 12 * bar_width) / 11
    max_value = max((month["count"] for month in stats["months"]), default=0) or 1
    bars: list[str] = []
    points: list[tuple[float, float]] = []

    for index, month in enumerate(stats["months"]):
        x = chart_x + index * (bar_width + gap)
        value = month["count"]
        bar_height = max(3, chart_height * value / max_value) if value else 2
        y = baseline - bar_height
        fill = ACCENT if value else RULE
        bar_delay = delay + 0.28 + index * 0.045
        bars.append(
            f'<rect class="bar" style="animation-delay:{bar_delay:.2f}s" '
            f'x="{x:.1f}" y="{y:.1f}" width="{bar_width}" height="{bar_height:.1f}" '
            f'rx="4" fill="{fill}"><title>{xml_text(month["label"].title())} '
            f'{month["year"]}: {value} contributions</title></rect>'
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
            f'<path class="trace" d="{path_data}" stroke-dasharray="{path_length:.1f}" '
            f'stroke-dashoffset="0"/>'
        )
    else:
        trace = (
            f'<path class="trace" d="{path_data}" stroke-dasharray="{path_length:.1f}" '
            f'stroke-dashoffset="{path_length:.1f}">'
            f'<animate attributeName="stroke-dashoffset" values="{path_length:.1f};0" '
            f'dur="1.15s" begin="{delay + 0.3:.2f}s" fill="freeze"/>'
            "</path>"
        )

    busiest_value = stats["busiest_label"]
    total_note = f'{stats["total"]:,} contributions in this window'
    month_labels = "".join(
        f'<text x="{chart_x + i * (bar_width + gap) + bar_width / 2:.1f}" y="387" '
        f'text-anchor="middle" class="mono" fill="{INK_3}" font-size="12">{month["label"]}</text>'
        for i, month in enumerate(stats["months"])
    )
    body = f'''
{card_background(width, height)}
<g class="enter">
  <text x="58" y="52" class="mono" fill="{ACCENT}" font-size="14" letter-spacing="1.7">GITHUB ACTIVITY  /  LAST 12 MONTHS</text>
  <text x="58" y="105" class="serif" fill="{INK}" font-size="48">A year, one day at a time.</text>
  <text x="942" y="54" text-anchor="end" class="mono" fill="{INK_3}" font-size="13" letter-spacing=".4">{xml_text(total_note.upper())}</text>
  <path d="M58 126h884" stroke="{RULE}" stroke-width="1.5"/>
  <text x="68" y="158" class="mono" fill="{INK_3}" font-size="12" letter-spacing="1.1">CURRENT STREAK</text>
  <text x="68" y="207" class="serif" fill="{INK}" font-size="39">{stats["streak"]} day{"s" if stats["streak"] != 1 else ""}</text>
  <text x="68" y="229" class="sans" fill="{INK_2}" font-size="13.5">consecutive active days</text>
  <path d="M341 145v88M624 145v88" stroke="{RULE}" stroke-width="1.5"/>
  <text x="371" y="158" class="mono" fill="{INK_3}" font-size="12" letter-spacing="1.1">ACTIVE DAYS</text>
  <text x="371" y="207" class="serif" fill="{INK}" font-size="39">{stats["active_days"]} days</text>
  <text x="371" y="229" class="sans" fill="{INK_2}" font-size="13.5">of the last year</text>
  <text x="654" y="158" class="mono" fill="{INK_3}" font-size="12" letter-spacing="1.1">BUSIEST DAY</text>
  <text x="654" y="207" class="serif" fill="{INK}" font-size="39">{xml_text(busiest_value)}</text>
  <text x="654" y="229" class="sans" fill="{INK_2}" font-size="13.5">{xml_text(stats["busiest_date"])} · contributions</text>
  <text x="64" y="272" class="mono" fill="{INK_3}" font-size="12" letter-spacing="1.1">CONTRIBUTIONS PER MONTH</text>
  <path d="M64 {baseline}h872" stroke="{RULE}" stroke-width="1.5"/>
  {''.join(bars)}
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
        f"Updated {updated}.",
        body,
        fonts,
        delay,
    )


def render_project(
    project: dict[str, Any], fonts: dict[str, str], delay: float
) -> str:
    body = f'''
{card_background(1000, 244)}
<g class="enter">
  <text x="62" y="55" class="mono" fill="{ACCENT}" font-size="14" letter-spacing="1.8">{project["number"]}  /  {xml_text(project["category"])}</text>
  <text x="60" y="124" class="serif" fill="{INK}" font-size="57" letter-spacing="-.5">{xml_text(project["name"])}</text>
  <text x="64" y="170" class="sans" fill="{INK_2}" font-size="20">{xml_text(project["description"])}</text>
  <text x="64" y="213" class="mono" fill="{INK_3}" font-size="13.5" letter-spacing=".5">{xml_text(project["stack"])}</text>
  <circle cx="911" cy="122" r="34" fill="{PAPER_ALT}" stroke="{RULE}" stroke-width="1.5"/>
  <path d="M897 122h27m-10-10 10 10-10 10" fill="none" stroke="{ACCENT}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
  <text x="911" y="185" text-anchor="middle" class="mono" fill="{INK_3}" font-size="10.5" letter-spacing=".8">VIEW REPO</text>
</g>
'''
    return svg_document(
        1000,
        244,
        project["name"],
        f'{project["description"]} Technologies: {project["stack"]}.',
        body,
        fonts,
        delay,
    )


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
            cells.append(
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2.2" '
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
    for index, tile in enumerate(TILES):
        write_card(
            f'tile-{tile["slug"]}.svg',
            render_tile(tile, fonts, 0.40 + index * 0.13),
        )
    write_card(
        "contributions.svg",
        render_contributions(days, stats, updated, fonts, 0.90),
    )
    for index, project in enumerate(PROJECTS):
        write_card(
            f'project-{project["slug"]}.svg',
            render_project(project, fonts, 1.28 + index * 0.30),
        )
    write_card(
        "contribution-graph.svg",
        render_graph(days, stats, updated, fonts, 2.28),
    )
    mode = "static final frame" if STATIC else "animated"
    print(f"Rendered 9 {mode} SVG cards into {CARDS_DIR.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
