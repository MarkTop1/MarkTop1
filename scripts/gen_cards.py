#!/usr/bin/env python3
"""生成 GitHub 主页用的黑白卡片 SVG（不依赖任何第三方服务）。

用法：
    python3 scripts/gen_cards.py            # 输出到 assets/
    GH_TOKEN=xxx python3 scripts/gen_cards.py

只用到标准库，GitHub Actions 里直接跑。
"""

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone

USER = os.environ.get("GH_USER", "MarkTop1")
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
OUT = os.environ.get("OUT_DIR", "assets")
# 想展示哪两个仓库，用逗号分隔；留空则按 Star 数自动取前两个
FEATURED = [s.strip() for s in os.environ.get("FEATURED", "").split(",") if s.strip()]

BG = "#0a0a0a"
BORDER = "#161616"
WHITE = "#ffffff"
MUTED = "#8f8f8f"
DIM = "#5a5a5a"
FAINT = "#4a4a4a"
RAMP = ["#ffffff", "#b4b4b4", "#8a8a8a", "#5c5c5c", "#3a3a3a"]

FONT = ("-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, "
        "'Helvetica Neue', Arial, 'PingFang SC', 'Microsoft YaHei', sans-serif")
MONO = ("ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, "
        "'Liberation Mono', monospace")


def api(path):
    req = urllib.request.Request("https://api.github.com" + path)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "profile-card-gen")
    if TOKEN:
        req.add_header("Authorization", "Bearer " + TOKEN)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def esc(text):
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


def em_width(text):
    """粗略估算文本宽度（单位 em）：CJK 算 1，其余算 0.55。"""
    total = 0.0
    for ch in text:
        total += 1.0 if ord(ch) > 0x2E80 else 0.55
    return total


def clip(text, max_em):
    text = (text or "").replace("\n", " ").strip()
    if em_width(text) <= max_em:
        return text
    out, acc = "", 0.0
    for ch in text:
        acc += 1.0 if ord(ch) > 0x2E80 else 0.55
        if acc > max_em - 0.7:
            break
        out += ch
    return out.rstrip() + "…"


def compact(n):
    if n >= 1000:
        return "{:.1f}k".format(n / 1000).replace(".0k", "k")
    return str(n)


LANG_COLORS = {
    "kotlin": "#a97bff", "javascript": "#f7df1e", "typescript": "#3178c6",
    "python": "#3776ab", "html": "#e34f26", "css": "#1572b6",
    "java": "#b07219", "go": "#00add8", "rust": "#dea584",
    "vue": "#41b883", "shell": "#89e051", "swift": "#f05138",
}
DEFAULT_LANG = "#8a8a8a"


def lang_color(name):
    return LANG_COLORS.get((name or "").lower(), DEFAULT_LANG)


def updated_ago(stamp):
    if not stamp:
        return ""
    try:
        then = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return ""
    days = (datetime.now(timezone.utc) - then).days
    if days <= 0:
        return "today"
    if days < 30:
        return "%dd ago" % days
    if days < 365:
        return "%dmo ago" % (days // 30)
    return "%dy ago" % (days // 365)


def write(name, svg):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(svg)
    print("wrote", path)


# ---------------------------------------------------------------- stats card
def stats_card(repos, user):
    stars = sum(r.get("stargazers_count", 0) for r in repos)
    items = [
        (compact(user.get("public_repos", len(repos))), "Repositories"),
        (compact(stars), "Stars"),
        (compact(user.get("followers", 0)), "Followers"),
        (compact(user.get("following", 0)), "Following"),
    ]
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="880" height="156" '
        'viewBox="0 0 880 156" fill="none" role="img" aria-label="GitHub stats">',
        '<rect x="0.5" y="0.5" width="879" height="155" rx="24" fill="%s" stroke="%s"/>' % (BG, BORDER),
    ]
    for i, (num, label) in enumerate(items):
        x = 48 + i * 196
        if i:
            parts.append('<rect x="%d" y="38" width="1" height="56" fill="#141414"/>' % (x - 22))
        parts.append(
            '<text x="%d" y="78" font-family="%s" font-size="42" font-weight="700" '
            'letter-spacing="-1.6" fill="%s">%s</text>' % (x, FONT, WHITE, esc(num))
        )
        parts.append(
            '<text x="%d" y="104" font-family="%s" font-size="10.5" letter-spacing="1.5" '
            'fill="%s">%s</text>' % (x, FONT, "#565656", esc(label.upper()))
        )
    parts.append("</svg>")
    return "".join(parts)


# ------------------------------------------------------------ language card
def langs_card(repos):
    totals = {}
    for repo in repos:
        lang = repo.get("language")
        if not lang:
            continue
        try:
            data = api("/repos/%s/%s/languages" % (USER, repo["name"]))
        except Exception:
            data = {}
        if data:
            for key, val in data.items():
                totals[key] = totals.get(key, 0) + val
        else:
            totals[lang] = totals.get(lang, 0) + 1

    ranked = sorted(totals.items(), key=lambda kv: -kv[1])[:4]
    grand = sum(v for _, v in ranked) or 1
    shares = [(k, v / grand) for k, v in ranked]

    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="880" height="124" '
        'viewBox="0 0 880 124" fill="none" role="img" aria-label="Top languages">',
        '<rect x="0.5" y="0.5" width="879" height="123" rx="24" fill="%s" stroke="%s"/>' % (BG, BORDER),
        '<text x="48" y="36" font-family="%s" font-size="10.5" letter-spacing="1.5" '
        'fill="%s">LANGUAGES</text>' % (FONT, "#4a4a4a"),
    ]

    bar_x, bar_w, bar_y, bar_h, gap = 48.0, 784.0, 50.0, 8.0, 3.0
    usable = bar_w - gap * max(0, len(shares) - 1)
    cursor = bar_x
    for idx, (name, share) in enumerate(shares):
        seg = max(3.0, usable * share)
        if idx == len(shares) - 1:
            seg = bar_x + bar_w - cursor          # 最后一段顶到最右边
        if seg <= 0:
            break
        parts.append(
            '<rect x="%.1f" y="%d" width="%.1f" height="%d" rx="4" fill="%s"/>'
            % (cursor, bar_y, seg, bar_h, RAMP[idx % len(RAMP)])
        )
        cursor += seg + gap

    cursor_x = 48.0
    for idx, (name, share) in enumerate(shares):
        color = RAMP[idx % len(RAMP)]
        parts.append('<circle cx="%.1f" cy="86" r="3.5" fill="%s"/>' % (cursor_x + 3, color))
        label = "%s %d%%" % (name, round(share * 100))
        parts.append(
            '<text x="%.1f" y="90" font-family="%s" font-size="12" fill="%s">%s</text>'
            % (cursor_x + 14, FONT, MUTED, esc(label))
        )
        cursor_x += 14 + em_width(label) * 12 + 26
    parts.append("</svg>")
    return "".join(parts)


# ---------------------------------------------------------------- repo card
def repo_card(repo):
    name = esc(clip(repo.get("name", ""), 20))
    raw_desc = (repo.get("description") or "").strip()
    lang = repo.get("language") or "—"
    desc = esc(clip(raw_desc, 29)) if raw_desc else "No description yet"
    desc_fill = "#7d7d7d" if raw_desc else "#3a3a3a"
    stars = repo.get("stargazers_count", 0)
    forks = repo.get("forks_count", 0)
    stamp = updated_ago(repo.get("pushed_at") or repo.get("updated_at"))

    meta = ['<circle cx="29" cy="100" r="3.4" fill="%s"/>' % lang_color(lang),
            '<text x="38" y="104" font-family="%s" font-size="11" fill="%s">%s</text>'
            % (FONT, DIM, esc(lang))]
    cursor = 38 + em_width(lang) * 11 + 16
    if stars:
        meta.append('<text x="%.0f" y="104" font-family="%s" font-size="11" fill="%s">★ %s</text>'
                    % (cursor, MONO, DIM, compact(stars)))
        cursor += 46
    if forks:
        meta.append('<text x="%.0f" y="104" font-family="%s" font-size="11" fill="%s">⑂ %s</text>'
                    % (cursor, MONO, DIM, compact(forks)))
    if stamp:
        meta.append('<text x="404" y="104" text-anchor="end" font-family="%s" font-size="10.5" '
                    'fill="#3f3f3f">updated %s</text>' % (FONT, esc(stamp)))

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="430" height="134" '
        'viewBox="0 0 430 134" fill="none" role="img" aria-label="%s">'
        '<rect x="0.5" y="0.5" width="429" height="133" rx="20" fill="%s" stroke="%s"/>'
        '<text x="26" y="44" font-family="%s" font-size="17" font-weight="600" '
        'letter-spacing="-0.4" fill="%s">%s</text>'
        '<text x="26" y="72" font-family="%s" font-size="12.5" fill="%s">%s</text>'
        "%s</svg>"
        % (name, BG, BORDER, FONT, WHITE, name, FONT, desc_fill, desc, "".join(meta))
    )


def main():
    user = api("/users/" + USER)
    repos = api("/users/%s/repos?per_page=100&sort=updated" % USER)
    repos = [r for r in repos if not r.get("fork")]

    write("card-stats.svg", stats_card(repos, user))
    write("card-langs.svg", langs_card(repos))

    if FEATURED:
        picked = [r for name in FEATURED for r in repos if r["name"].lower() == name.lower()]
    else:
        picked = sorted(repos, key=lambda r: -r.get("stargazers_count", 0))

    picked = picked[:2]
    for idx, repo in enumerate(picked, start=1):
        write("card-repo-%d.svg" % idx, repo_card(repo))

    print("featured:", ", ".join(r["name"] for r in picked))


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as exc:
        print("HTTP error:", exc.code, exc.reason)
        raise SystemExit(1)
