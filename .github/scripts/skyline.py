"""Render the contribution calendar as an animated night-city skyline SVG.

Each building is one week of contributions: taller buildings and more lit
windows mean a busier week. Run from a GitHub Action:

    GITHUB_TOKEN=... python skyline.py <username> <output.svg>
"""
import datetime as dt
import json
import math
import os
import random
import sys
import urllib.request

W, H = 880, 330
GROUND = 282
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"
CAP_COLORS = ["#334155", "#6366F1", "#8B5CF6", "#3B82F6", "#22D3EE"]
CAR_COLORS = ["#F472B6", "#38BDF8", "#FBBF24", "#A78BFA", "#34D399"]

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { firstDay contributionDays { contributionCount } }
      }
    }
  }
}
"""


def fetch_weeks(login, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    if "errors" in payload:
        raise SystemExit(f"GraphQL error: {payload['errors']}")
    cal = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = [(w["firstDay"], sum(d["contributionCount"] for d in w["contributionDays"])) for w in cal["weeks"]]
    return cal["totalContributions"], weeks


def stars(rng):
    out = []
    for _ in range(70):
        x, y = rng.uniform(8, W - 8), rng.uniform(8, GROUND - 120)
        r = rng.choice([0.6, 0.8, 1.0, 1.3])
        out.append(f'<circle class="tw" cx="{x:.1f}" cy="{y:.1f}" r="{r}" '
                   f'style="animation-duration:{rng.uniform(2, 5):.1f}s;animation-delay:-{rng.uniform(0, 5):.1f}s"/>')
    return "".join(out)


def buildings(rng, weeks):
    peak = max((c for _, c in weeks), default=0) or 1
    n = len(weeks)
    bw, gap = 13, 3
    x0 = (W - (n * bw + (n - 1) * gap)) / 2
    out, months, last_month = [], [], None
    for i, (first_day, count) in enumerate(weeks):
        ratio = math.sqrt(count / peak)
        level = 0 if count == 0 else min(4, 1 + int(ratio * 4))
        h = 16 + 150 * ratio
        x, y = x0 + i * (bw + gap), GROUND - h
        parts = [f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw}" height="{h:.1f}" rx="1.5" fill="url(#bld)"/>',
                 f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw}" height="2.5" rx="1" fill="{CAP_COLORS[level]}"/>']
        lit_p = 0.06 + 0.17 * level
        wy = y + 7
        while wy < GROUND - 7:
            for wx in (x + 2.5, x + 7.5):
                if rng.random() < lit_p:
                    cls = ' class="fl"' if rng.random() < 0.18 else ""
                    style = (f' style="animation-duration:{rng.uniform(3, 8):.1f}s;'
                             f'animation-delay:-{rng.uniform(0, 8):.1f}s"' if cls else "")
                    parts.append(f'<rect{cls} x="{wx:.1f}" y="{wy:.1f}" width="3" height="3" fill="#FDE68A"{style}/>')
            wy += 7
        out.append(f'<g>{"".join(parts)}</g>')

        month = first_day[:7]
        if month != last_month:
            if last_month is not None and x < W - 130:
                label = dt.date.fromisoformat(first_day).strftime("%b")
                months.append(f'<text x="{x:.1f}" y="{GROUND + 40}" class="m">{label}</text>')
            last_month = month
    return "".join(out), "".join(months), peak


def cars(rng):
    out = []
    for lane, y, direction in ((0, GROUND + 9, 1), (1, GROUND + 17, -1)):
        for _ in range(3):
            color = rng.choice(CAR_COLORS)
            dur = rng.uniform(9, 15)
            delay = rng.uniform(0, dur)
            light_x = 13 if direction == 1 else -2
            out.append(
                f'<g class="car{lane}" style="animation-duration:{dur:.1f}s;animation-delay:-{delay:.1f}s">'
                f'<rect x="0" y="{y - 3}" width="13" height="5" rx="2" fill="{color}"/>'
                f'<rect x="{light_x}" y="{y - 1.5}" width="2" height="2" fill="#FEF3C7"/></g>')
    return "".join(out)


def render(login, total, weeks):
    rng = random.Random(f"{login}-{len(weeks)}")
    city, months, peak = buildings(rng, weeks)
    updated = dt.date.today().isoformat()
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <defs>
    <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#070B1A"/><stop offset=".65" stop-color="#1E1B4B"/><stop offset="1" stop-color="#312E81"/>
    </linearGradient>
    <linearGradient id="bld" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#1E293B"/><stop offset="1" stop-color="#0B1120"/>
    </linearGradient>
    <linearGradient id="meteor" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>
    </linearGradient>
    <radialGradient id="glow"><stop offset="0" stop-color="#FDE68A" stop-opacity=".45"/><stop offset="1" stop-color="#FDE68A" stop-opacity="0"/></radialGradient>
    <clipPath id="frame"><rect width="{W}" height="{H}" rx="16"/></clipPath>
    <style>
      .tw {{ fill: #fff; animation: tw ease-in-out infinite alternate; }}
      @keyframes tw {{ from {{ opacity: .15; }} to {{ opacity: 1; }} }}
      .fl {{ animation: fl steps(1) infinite; }}
      @keyframes fl {{ 0%, 70% {{ opacity: 1; }} 71%, 100% {{ opacity: .1; }} }}
      .car0 {{ animation: drive linear infinite; }}
      .car1 {{ animation: back linear infinite; }}
      @keyframes drive {{ from {{ transform: translateX(-30px); }} to {{ transform: translateX({W + 30}px); }} }}
      @keyframes back {{ from {{ transform: translateX({W + 30}px); }} to {{ transform: translateX(-30px); }} }}
      .meteor {{ animation: meteor 7s ease-in infinite; opacity: 0; }}
      @keyframes meteor {{ 0%, 80% {{ opacity: 0; transform: translate(0, 0); }} 83% {{ opacity: 1; }}
                          92%, 100% {{ opacity: 0; transform: translate(-260px, 110px); }} }}
      .moon {{ animation: moon 6s ease-in-out infinite alternate; transform-origin: 800px 52px; }}
      @keyframes moon {{ from {{ transform: scale(1); }} to {{ transform: scale(1.15); }} }}
      .t {{ font-family: {FONT}; fill: #F8FAFC; }}
      .s {{ font-family: {FONT}; fill: #A5B4FC; }}
      .m {{ font-family: {FONT}; fill: #64748B; font-size: 10px; }}
    </style>
  </defs>
  <g clip-path="url(#frame)">
    <rect width="{W}" height="{H}" fill="url(#sky)"/>
    {stars(rng)}
    <circle class="moon" cx="800" cy="52" r="46" fill="url(#glow)"/>
    <circle cx="800" cy="52" r="17" fill="#FDE68A"/>
    <circle cx="807" cy="47" r="15" fill="#1A1744" opacity=".35"/>
    <g class="meteor"><line x1="640" y1="42" x2="704" y2="16" stroke="url(#meteor)" stroke-width="2" stroke-linecap="round"/></g>
    <text x="28" y="44" class="t" font-size="26" font-weight="800">{total:,} contributions</text>
    <text x="28" y="68" class="s" font-size="13.5">in the last year · each building is one week · busiest week: {peak}</text>
    {city}
    <rect x="0" y="{GROUND}" width="{W}" height="{H - GROUND}" fill="#0B1020"/>
    <line x1="0" y1="{GROUND + 13}" x2="{W}" y2="{GROUND + 13}" stroke="#334155" stroke-dasharray="8 8"/>
    {cars(rng)}
    {months}
    <text x="{W - 20}" y="{H - 10}" class="m" text-anchor="end">updated {updated}</text>
  </g>
</svg>
'''


def main():
    login, out_path = sys.argv[1], sys.argv[2]
    total, weeks = fetch_weeks(login, os.environ["GITHUB_TOKEN"])
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(render(login, total, weeks))


if __name__ == "__main__":
    main()
