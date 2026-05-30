import os, json, html, urllib.request
from datetime import datetime, timedelta, timezone
USERNAME = "darmayo"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
HEADERS = {"Accept":"application/vnd.github+json","User-Agent":"github-profile-dashboard"}
if TOKEN: HEADERS["Authorization"] = "Bearer " + TOKEN
def gh(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r: return json.loads(r.read().decode("utf-8"))
def gql(query, variables=None):
    data = json.dumps({"query":query,"variables":variables or {}}).encode()
    headers = {"Content-Type":"application/json","User-Agent":"github-profile-dashboard","Authorization":"Bearer " + TOKEN}
    req = urllib.request.Request("https://api.github.com/graphql", data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r: return json.loads(r.read().decode("utf-8"))
def safe_int(v):
    try: return int(v or 0)
    except Exception: return 0
def fetch_data():
    user = gh(f"https://api.github.com/users/{USERNAME}")
    repos = gh(f"https://api.github.com/users/{USERNAME}/repos?per_page=100&sort=updated")
    public_repos = safe_int(user.get("public_repos"))
    followers = safe_int(user.get("followers"))
    following = safe_int(user.get("following"))
    created_at = user.get("created_at", "2023-01-01T00:00:00Z")[:10]
    stars = forks = updated_repos = 0
    lang_count = {}
    now = datetime.now(timezone.utc)
    for repo in repos:
        stars += safe_int(repo.get("stargazers_count"))
        forks += safe_int(repo.get("forks_count"))
        lang = repo.get("language") or "Other"
        lang_count[lang] = lang_count.get(lang, 0) + 1
        updated = repo.get("updated_at")
        if updated:
            dt = datetime.fromisoformat(updated.replace("Z","+00:00"))
            if now - dt <= timedelta(days=90): updated_repos += 1
    total_contrib, days = 0, []
    try:
        q = "query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}"
        result = gql(q, {"login": USERNAME})
        cal = result["data"]["user"]["contributionsCollection"]["contributionCalendar"]
        total_contrib = safe_int(cal.get("totalContributions"))
        for w in cal.get("weeks", []):
            for d in w.get("contributionDays", []): days.append((d["date"], safe_int(d["contributionCount"])))
    except Exception: pass
    return {"public_repos":public_repos,"followers":followers,"following":following,"created_at":created_at,"stars":stars,"forks":forks,"updated_repos":updated_repos,"lang_count":lang_count,"total_contrib":total_contrib,"recent_days":days[-31:],"generated_at":datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}
def card(x,y,w,h,title,value,sub,accent):
    return f"""<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="#111827" stroke="#30363d"/><text x="{x+18}" y="{y+28}" class="label">{html.escape(str(title))}</text><text x="{x+18}" y="{y+66}" class="value" fill="{accent}">{html.escape(str(value))}</text><text x="{x+18}" y="{y+92}" class="sub">{html.escape(str(sub))}</text>"""
def line_chart(days,x,y,w,h):
    if not days: days = [(str(i),0) for i in range(31)]
    vals = [v for _,v in days]; maxv = max(max(vals), 1); pts=[]
    for i,(_,v) in enumerate(days):
        px = x + (i/max(len(days)-1,1))*w; py = y + h - (v/maxv)*h; pts.append((px,py))
    path = " ".join([("M" if i==0 else "L") + f"{px:.1f},{py:.1f}" for i,(px,py) in enumerate(pts)])
    area = path + f" L{x+w},{y+h} L{x},{y+h} Z"
    grid = ""
    for i in range(5):
        gy = y + i*h/4; grid += f"""<line x1="{x}" y1="{gy:.1f}" x2="{x+w}" y2="{gy:.1f}" stroke="#263241" stroke-width="1"/>"""
    for i in range(0, len(days), max(len(days)//6,1)):
        gx = x + (i/max(len(days)-1,1))*w; grid += f"""<line x1="{gx:.1f}" y1="{y}" x2="{gx:.1f}" y2="{y+h}" stroke="#1f2937" stroke-width="1"/>"""
    dots = "".join([f"""<circle cx="{px:.1f}" cy="{py:.1f}" r="2.5" fill="#58a6ff"/>""" for px,py in pts])
    return f"""<text x="{x}" y="{y-18}" class="panel-title">Contribution Activity · Last 31 Days</text><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="#0b1220" stroke="#30363d"/>{grid}<path d="{area}" fill="#1f6feb" opacity="0.18"/><path d="{path}" fill="none" stroke="#58a6ff" stroke-width="3"/>{dots}<text x="{x}" y="{y+h+22}" class="sub">max/day: {maxv}</text>"""
def lang_bars(lang_count,x,y,w):
    items = sorted(lang_count.items(), key=lambda kv: kv[1], reverse=True)[:6]
    total = sum(v for _,v in items) or 1; colors=["#58a6ff","#bc8cff","#3fb950","#e3b341","#f85149","#8b949e"]
    out = f"""<text x="{x}" y="{y}" class="panel-title">Repository Languages</text>"""
    y0 = y + 24
    for i,(lang,count) in enumerate(items):
        bw = int((w-130)*(count/total)); yy = y0 + i*30; color = colors[i % len(colors)]
        out += f"""<text x="{x}" y="{yy+14}" class="sub">{html.escape(str(lang))}</text><rect x="{x+110}" y="{yy}" width="{w-130}" height="12" rx="6" fill="#1f2937"/><rect x="{x+110}" y="{yy}" width="{bw}" height="12" rx="6" fill="{color}"/><text x="{x+w-10}" y="{yy+12}" class="sub" text-anchor="end">{count}</text>"""
    return out
def generate_svg(d):
    return f"""<svg width="900" height="650" viewBox="0 0 900 650" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="panel" x1="0" x2="1"><stop offset="0%" stop-color="#0d1117"/><stop offset="100%" stop-color="#111827"/></linearGradient><style>.title{{font:700 24px Inter,Segoe UI,Arial,sans-serif;fill:#fff}}.panel-title{{font:700 15px Inter,Segoe UI,Arial,sans-serif;fill:#c9d1d9}}.label{{font:600 13px Inter,Segoe UI,Arial,sans-serif;fill:#8b949e}}.value{{font:800 30px Inter,Segoe UI,Arial,sans-serif}}.sub{{font:500 12px Inter,Segoe UI,Arial,sans-serif;fill:#8b949e}}.small{{font:500 11px Inter,Segoe UI,Arial,sans-serif;fill:#6e7681}}</style></defs><rect width="900" height="650" rx="18" fill="#0d1117"/><rect x="16" y="16" width="868" height="618" rx="18" fill="url(#panel)" stroke="#30363d"/><text x="36" y="54" class="title">📊 GitHub Monitoring Dashboard</text><text x="36" y="78" class="sub">custom SVG dashboard · updated automatically by GitHub Actions</text><text x="864" y="78" class="small" text-anchor="end">updated: {html.escape(d["generated_at"])}</text>{card(36,110,190,110,"Contributions",d["total_contrib"],"last 12 months","#58a6ff")}{card(246,110,190,110,"Repositories",d["public_repos"],str(d["updated_repos"])+" updated recently","#bc8cff")}{card(456,110,190,110,"Stars",d["stars"],str(d["forks"])+" forks","#e3b341")}{card(666,110,180,110,"Followers",d["followers"],"following "+str(d["following"]),"#3fb950")}{line_chart(d["recent_days"],46,280,520,190)}<rect x="602" y="250" width="244" height="250" rx="14" fill="#111827" stroke="#30363d"/>{lang_bars(d["lang_count"],626,284,200)}<rect x="46" y="545" width="800" height="52" rx="14" fill="#0b1220" stroke="#30363d"/><text x="70" y="576" class="panel-title">GitHub since {html.escape(d["created_at"][:4])}</text><text x="250" y="576" class="sub">Security learning · SOC · Web security · Mobile security · Research notes</text></svg>"""
if __name__ == "__main__":
    open("github-dashboard.svg","w",encoding="utf-8").write(generate_svg(fetch_data()))
