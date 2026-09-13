#!/usr/bin/env python3
"""Generate GitHub-safe, self-contained SVG panels using GitHub GraphQL data."""
import argparse
from datetime import datetime, timedelta, timezone
from html import escape
import json
import os
from pathlib import Path
import textwrap
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
BG, FG, MUTED, GREEN, CYAN = '#060606', '#e6fbfb', '#8a8a8a', '#3fb950', '#39c5cf'


def text(x, y, value, size=12, color=FG, extra=''):
    return f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" {extra}>{escape(str(value))}</text>'


def rect(x, y, w, h, fill='none', stroke='#252525'):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}"/>'


def svg(width, height, title, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title, quote=True)}">'
            f'<title>{escape(title)}</title>{rect(0, 0, width, height, BG)}'
            f'<g font-family="ui-monospace, SFMono-Regular, Consolas, monospace">{body}</g></svg>\n')


def fetch(login, now):
    start = (now - timedelta(days=29)).replace(hour=0, minute=0, second=0, microsecond=0)
    query = '''query($login:String!, $from:DateTime!, $to:DateTime!) {
      user(login:$login) { login name url
        year: contributionsCollection { contributionCalendar {
          weeks { contributionDays { date contributionCount color } }
        } }
        contributionsCollection(from:$from, to:$to) {
          totalCommitContributions totalPullRequestContributions
          totalIssueContributions totalPullRequestReviewContributions
          totalRepositoriesWithContributedCommits
          contributionCalendar { weeks { contributionDays { date contributionCount } } }
        }
      }
    }'''
    variables = {'login': login, 'from': start.isoformat(), 'to': now.isoformat()}
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if not token:
        raise RuntimeError('Set GH_TOKEN or GITHUB_TOKEN; no synthetic data is generated.')
    request = urllib.request.Request('https://api.github.com/graphql',
        data=json.dumps({'query': query, 'variables': variables}).encode(),
        headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json',
                 'User-Agent': 'profile-readme-generator'})
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.load(response)
    if payload.get('errors') or not payload.get('data', {}).get('user'):
        raise RuntimeError(f'GitHub GraphQL failed: {payload.get("errors", "user not found")}')
    user = payload['data']['user']
    c = user['contributionsCollection']
    days = [d for w in c['contributionCalendar']['weeks'] for d in w['contributionDays']
            if start.date().isoformat() <= d['date'] <= now.date().isoformat()]
    return {'login': user['login'], 'name': user['name'] or user['login'],
            'updated': now.strftime('%Y-%m-%d %H:%M UTC'), 'from': start.date().isoformat(),
            'to': now.date().isoformat(), 'commits': c['totalCommitContributions'],
            'prs': c['totalPullRequestContributions'], 'issues': c['totalIssueContributions'],
            'reviews': c['totalPullRequestReviewContributions'],
            'repositories': c['totalRepositoriesWithContributedCommits'],
            'active_days': sum(d['contributionCount'] > 0 for d in days),
            'calendar': user['year']['contributionCalendar']['weeks']}


def dna(data):
    # Transparent activity indices, not personality assessments.
    return [(label, min(100, round(100 * data[key] / target))) for label, key, target in [
        ('Builder', 'commits', 60), ('Reviewer', 'reviews', 20),
        ('Collaborator', 'prs', 10), ('Reporter', 'issues', 10),
        ('Explorer', 'repositories', 5)]]


def snake(data):
    weeks = data['calendar']
    body = text(24, 32, '[ CONTRIBUTION SNAKE / LAST YEAR ]', 11, MUTED)
    cells = []
    for x, week in enumerate(weeks):
        column = []
        for day in week['contributionDays']:
            # GitHub calendar rows run Sunday through Saturday.
            y = (datetime.fromisoformat(day['date']).weekday() + 1) % 7
            px, py = 24+x*14, 65+y*14
            color = day['color'] if day['contributionCount'] else '#161b22'
            body += f'<g><title>{escape(day["date"])}: {day["contributionCount"]} contributions</title>{rect(px, py, 10, 10, color, color)}</g>'
            column.append((px, py))
        cells.extend(reversed(column) if x % 2 else column)
    if cells:
        for segment in reversed(range(5)):
            path = cells[-segment:] + cells[:-segment] if segment else cells
            values = ';'.join(f'{x} {y}' for x, y in path + path[:1])
            x, y = path[0]
            body += (f'<g transform="translate({x} {y})"><animateTransform attributeName="transform" '
                     f'type="translate" values="{values}" calcMode="discrete" dur="60s" repeatCount="indefinite"/>'
                     f'<rect width="10" height="10" rx="3" fill="{["#e879f9", "#d946ef", "#c026d3", "#a21caf", "#86198f"][segment]}"/></g>')
    body += text(24, 194, 'LIVE DATA · DAILY SYNC / ' + data['updated'], 10, MUTED)
    return svg(max(800, 48+len(weeks)*14), 220, 'Animated snake over actual GitHub contributions for the last year', body)


def render(data):
    config = json.loads((ROOT / 'ref/gitascii.json').read_text())
    bio_config = next(w['config'] for w in config['widgets'] if w['widgetId'] == 'bio')
    body = text(24, 26, f'NODE//@{data["login"]}  ·  SIG:CONNECTED  ·  RETRO CRT', 10, MUTED)
    body += text(640, 26, '● REC / PROFILE', 10, '#ff5c5c')
    body += '<path d="M24 38H776" stroke="#30363d"/>'
    body += text(400, 67, '[ SYSTEM :: TERMINAL PROFILE :: RETRO CRT ]', 10, FG, 'text-anchor="middle" letter-spacing="2"')
    body += text(402, 124, '> ' + data['name'], 39, '#754b59', 'text-anchor="middle" font-weight="bold"')
    body += text(400, 122, '> ' + data['name'], 39, FG, 'text-anchor="middle" font-weight="bold"')
    body += text(400, 147, f'[ {data["name"]} // @{data["login"]} ]', 10, MUTED, 'text-anchor="middle"')
    body += text(400, 170, 'Linux Kernel Developer // Terminal Purist', 12, FG, 'text-anchor="middle"')
    portrait = (ROOT / 'assets/portrait.svg').read_text()
    body += f'<svg x="257.5" y="195" width="285" height="180" viewBox="0 0 160 160">{portrait}</svg>'
    body += rect(257.5, 195, 285, 180, 'none', '#8a8a8a')
    for i, color in enumerate([FG, '#e6dc57', GREEN, CYAN, '#b75aff', '#ff5c5c']):
        body += rect(258.5+i*47, 196, 47, 3, color, color)
    body += text(267.5, 211, 'CH 03 · CAM-01', 8) + text(500.5, 211, 'LIVE', 8, '#ff5c5c')
    for y in range(215, 374, 3):
        body += f'<path d="M258.5 {y}H541.5" stroke="#060606" opacity=".35"/>'
    body += text(267.5, 367, 'FEED: GITHUB AVATAR / STATIC CAPTURE', 8)
    body += text(400, 407, '“Once I told the computer to do something and it did it exactly how I told it to.”', 12, FG, 'text-anchor="middle"')
    body += text(24, 465, 'TELEMETRY SYNC: ' + data['updated'], 10, MUTED)
    header = svg(800, 482, 'Surveillance terminal profile — ' + data['name'], body)

    lines = textwrap.wrap(' '.join(bio_config['customBio'].split()), width=91)
    body = text(24, 32, '[ BIOGRAPHY ]', 11, MUTED, 'letter-spacing="2"')
    for i, line in enumerate(lines):
        # Justify full lines between equal 24px margins; keep the final line natural.
        extra = 'textLength="752" lengthAdjust="spacing"' if i < len(lines)-1 else ''
        body += text(24, 63+i*21, line, 13, extra=extra)
    body += text(24, 88+len(lines)*21, bio_config['customBlog'], 12, '#c5ff4a')
    bio = svg(800, 110+len(lines)*21, 'Biography', body)

    body = text(24, 30, '[ CODING VELOCITY ]', 12, GREEN)
    body += text(424, 30, '[ CODING DNA / ACTIVITY INDICES ]', 12, GREEN)
    body += text(24, 56, f'{data["from"]} → {data["to"]} / 30 days', 10, MUTED)
    for i, (label, key) in enumerate([('Commits', 'commits'), ('Pull requests', 'prs'), ('Issues opened', 'issues'), ('PR reviews', 'reviews')]):
        y = 89+i*30
        body += text(24, y, label, 12) + rect(170, y-11, 110, 12, '#161b22')
        body += rect(170, y-11, 110*data[key]/max(1, data['commits'], data['prs'], data['issues'], data['reviews']), 12, GREEN, GREEN)
        body += text(352, y, data[key], 12, CYAN, 'text-anchor="end"')
    body += text(24, 221, f'Avg. commits/day: {data["commits"]/30:.1f}', 12, '#e6c657')
    body += text(24, 247, f'Active days: {data["active_days"]}/30', 11, MUTED)
    for i, (label, score) in enumerate(dna(data)):
        y = 66+i*31
        body += text(424, y, label, 12) + rect(545, y-11, 140, 14, '#161b22')
        body += rect(545, y-11, 1.4*score, 14, GREEN, GREEN)
        body += text(744, y, f'{score}%', 12, CYAN, 'text-anchor="end"')
    scores = dna(data)
    primary = max(scores, key=lambda item: item[1])[0] if any(s for _, s in scores) else 'Quiet signal'
    body += text(424, 235, 'PRIMARY SIGNAL > ' + primary.upper(), 11, '#e6c657')
    body += text(424, 257, 'Activity / fixed targets; capped at 100%.', 10, MUTED)
    return {'header.svg': header, 'bio.svg': bio, 'telemetry.svg': svg(800, 280, '30-day coding velocity and activity DNA', body)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--login', default='vishsant')
    parser.add_argument('--snapshot', type=Path, help='Render a previously fetched snapshot offline')
    args = parser.parse_args()
    data = json.loads(args.snapshot.read_text()) if args.snapshot else fetch(args.login, datetime.now(timezone.utc))
    panels = render(data)
    panels['snake.svg'] = snake(data)
    out = ROOT / 'assets'
    out.mkdir(exist_ok=True)
    for name, content in panels.items():
        (out / name).write_text(content)
    (out / 'activity.json').write_text(json.dumps(data, indent=2) + '\n')


if __name__ == '__main__':
    main()
