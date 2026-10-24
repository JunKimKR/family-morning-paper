#!/usr/bin/env python3
"""우리집 아침신문 차트 생성기.

JSON 명세를 읽어 _includes/charts/ 아래에 인라인 SVG를 만든다.
색은 사이트 CSS 변수(--up, --down, --ink, --muted, --line)를 그대로 써서
다크 모드에서도 자동으로 맞는다.

사용법:
  python3 tools/charts.py spec.json

spec.json 예시:
{
  "date": "2026-10-24",
  "charts": [
    {"name": "moves", "type": "bars", "title": "...", "unit": "%",
     "items": [{"label": "코스피", "value": 0.30}, ...]},
    {"name": "flows", "type": "bars", "title": "...", "unit": "억 원",
     "items": [{"label": "외국인", "value": -9829}, ...]},
    {"name": "journey", "type": "journey", "title": "...",
     "points": [{"label": "전날 마감", "value": 5533.77}, ...]},
    {"name": "kospi", "type": "history", "title": "...", "column": "kospi", "days": 20}
  ]
}
"bars"는 0을 가운데 두고 오르면 빨강(오른쪽), 내리면 파랑(왼쪽)으로 그린다.
"history"는 _data/market_history.csv의 열 하나를 선 그래프로 그린다.
"""
import csv
import json
import os
import sys
from html import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "_includes", "charts")
HISTORY = os.path.join(ROOT, "_data", "market_history.csv")

W = 400
FONT = 'font-family="inherit"'


def fmt(v, unit=""):
    if unit == "%":
        return f"{v:+.2f}%"
    if abs(v) >= 1000:
        s = f"{abs(v):,.0f}"
    elif float(v).is_integer():
        s = f"{abs(v):.0f}"
    else:
        s = f"{abs(v):,.2f}"
    sign = "+" if v > 0 else ("−" if v < 0 else "")
    return f"{sign}{s}{(' ' + unit) if unit and unit != '%' else ''}"


def wrap(svg_body, h, title, desc):
    return (
        f'<figure class="chart">\n'
        f'<figcaption>{escape(title)}</figcaption>\n'
        f'<svg viewBox="0 0 {W} {h}" width="100%" role="img" aria-label="{escape(desc)}" '
        f'style="max-width:100%;height:auto;display:block" {FONT}>\n{svg_body}</svg>\n'
        f'</figure>\n'
    )


def bars(c):
    items = c["items"]
    unit = c.get("unit", "")
    row, top, label_w = 40, 6, 104
    h = top + row * len(items) + 8
    plot_l, plot_r = label_w, W - 12
    mid = (plot_l + plot_r) / 2
    half = (plot_r - plot_l) / 2 - 62  # 값 라벨 자리
    m = max(abs(i["value"]) for i in items) or 1
    out = [f'<line x1="{mid}" y1="{top - 4}" x2="{mid}" y2="{h - 4}" stroke="var(--muted)" stroke-width="1.5"/>']
    for k, it in enumerate(items):
        v = it["value"]
        y = top + k * row
        cy = y + row / 2
        bw = max(abs(v) / m * half, 3)
        color = "var(--up)" if v > 0 else ("var(--down)" if v < 0 else "var(--muted)")
        x = mid if v >= 0 else mid - bw
        tip = f'{it["label"]} {fmt(v, unit)}'
        out.append(f'<g><title>{escape(tip)}</title>')
        out.append(f'<rect x="0" y="{y}" width="{W}" height="{row}" fill="transparent"/>')
        out.append(f'<text x="0" y="{cy + 6}" font-size="15" font-weight="600" fill="var(--ink)">{escape(it["label"])}</text>')
        out.append(f'<rect x="{x:.1f}" y="{cy - 10}" width="{bw:.1f}" height="20" rx="4" fill="{color}"/>')
        tx = mid + bw + 8 if v >= 0 else mid - bw - 8
        anchor = "start" if v >= 0 else "end"
        out.append(f'<text x="{tx:.1f}" y="{cy + 6}" font-size="14" font-weight="700" text-anchor="{anchor}" fill="var(--ink)">{escape(fmt(v, unit))}</text>')
        out.append('</g>')
    desc = ", ".join(f'{i["label"]} {fmt(i["value"], unit)}' for i in items)
    return wrap("\n".join(out) + "\n", h, c["title"], desc)


def line_path(points, x0, x1, y0, y1):
    vals = [p["value"] for p in points]
    lo, hi = min(vals), max(vals)
    pad = (hi - lo) * 0.12 or 1
    lo, hi = lo - pad, hi + pad
    n = len(points)

    def X(i):
        return x0 + (x1 - x0) * (i / (n - 1) if n > 1 else 0.5)

    def Y(v):
        return y1 - (v - lo) / (hi - lo) * (y1 - y0)

    return X, Y, lo, hi


def journey(c):
    pts = c["points"]
    h = 250
    x0, x1, y0, y1 = 44, W - 44, 34, 180
    X, Y, lo, hi = line_path(pts, x0, x1, y0, y1)
    base = pts[0]["value"]
    out = [
        f'<line x1="{x0 - 30}" y1="{Y(base):.1f}" x2="{x1 + 30}" y2="{Y(base):.1f}" stroke="var(--muted)" stroke-width="1" stroke-dasharray="4 4"/>',
    ]
    d = " ".join(f'{"M" if i == 0 else "L"}{X(i):.1f},{Y(p["value"]):.1f}' for i, p in enumerate(pts))
    out.append(f'<path d="{d}" fill="none" stroke="var(--ink)" stroke-width="2.5" stroke-linejoin="round"/>')
    for i, p in enumerate(pts):
        v = p["value"]
        color = "var(--up)" if v > base else ("var(--down)" if v < base else "var(--muted)")
        x, y = X(i), Y(v)
        below = v < base
        ly = y + 30 if below else y - 16
        out.append(f'<g><title>{escape(p["label"])} {v:,.2f}</title>')
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{color}" stroke="var(--paper)" stroke-width="2"/>')
        out.append(f'<text x="{x:.1f}" y="{ly:.1f}" font-size="14" font-weight="700" text-anchor="middle" fill="var(--ink)">{v:,.2f}</text>')
        out.append(f'<text x="{x:.1f}" y="{h - 12}" font-size="13" text-anchor="middle" fill="var(--muted)">{escape(p["label"])}</text>')
        out.append('</g>')
    desc = ", ".join(f'{p["label"]} {p["value"]:,.2f}' for p in pts)
    return wrap("\n".join(out) + "\n", h, c["title"], desc)


def history(c):
    col = c["column"]
    days = c.get("days", 20)
    with open(HISTORY, encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r.get(col)]
    rows = rows[-days:]
    if len(rows) < 2:
        return ""
    pts = [{"label": r["date"][5:].replace("-", "/"), "value": float(r[col])} for r in rows]
    h = 220
    x0, x1, y0, y1 = 8, W - 64, 20, 180
    X, Y, lo, hi = line_path(pts, x0, x1, y0, y1)
    out = []
    for frac in (0, 0.5, 1):
        v = lo + (hi - lo) * frac
        out.append(f'<line x1="{x0}" y1="{Y(v):.1f}" x2="{x1}" y2="{Y(v):.1f}" stroke="var(--line)" stroke-width="1"/>')
        out.append(f'<text x="{x1 + 8}" y="{Y(v) + 5:.1f}" font-size="13" fill="var(--muted)">{v:,.0f}</text>')
    d = " ".join(f'{"M" if i == 0 else "L"}{X(i):.1f},{Y(p["value"]):.1f}' for i, p in enumerate(pts))
    out.append(f'<path d="{d}" fill="none" stroke="var(--accent)" stroke-width="2.5" stroke-linejoin="round"/>')
    for i, p in enumerate(pts):
        out.append(f'<g><title>{p["label"]} {p["value"]:,.2f}</title><circle cx="{X(i):.1f}" cy="{Y(p["value"]):.1f}" r="10" fill="transparent"/></g>')
    last = pts[-1]
    out.append(f'<circle cx="{X(len(pts) - 1):.1f}" cy="{Y(last["value"]):.1f}" r="5" fill="var(--accent)"/>')
    out.append(f'<text x="{x0}" y="{h - 10}" font-size="13" fill="var(--muted)">{pts[0]["label"]}</text>')
    out.append(f'<text x="{x1}" y="{h - 10}" font-size="13" text-anchor="end" fill="var(--muted)">{last["label"]}</text>')
    desc = f'{pts[0]["label"]}부터 {last["label"]}까지 {len(pts)}일, 마지막 값 {last["value"]:,.2f}'
    return wrap("\n".join(out) + "\n", h, c["title"], desc)


KINDS = {"bars": bars, "journey": journey, "history": history}


def main(path):
    with open(path, encoding="utf-8") as f:
        spec = json.load(f)
    os.makedirs(OUT, exist_ok=True)
    for c in spec["charts"]:
        svg = KINDS[c["type"]](c)
        name = f'{spec["date"]}-{c["name"]}.svg'
        if not svg:
            print(f"skip {name}: 데이터 부족")
            continue
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"wrote _includes/charts/{name}  →  {{% include charts/{name} %}}")


if __name__ == "__main__":
    main(sys.argv[1])
