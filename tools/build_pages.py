#!/usr/bin/env python3
"""把本仓库的 markdown 生成成 GitHub Pages 的静态站（输出到 _site/）。

为什么不直接用 Jekyll：Jekyll 只处理带 YAML front matter 的 markdown，
而给 README 加 front matter 会让 GitHub 仓库页顶部多出一张表格。更重要的是
默认主题给不了我们要的那几样东西——准确的 <title>、meta description、
canonical、以及 FAQ 的结构化数据。所以这里自己渲染，产物带 .nojekyll。

用法：
    python3 tools/build_pages.py            # 生成到 _site/
    python3 tools/build_pages.py --check    # 只校验链接，不写文件

产物推到 gh-pages 分支，main 分支保持纯 markdown。
"""

import argparse
import html
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "_site"
SITE = "https://code2ai-codes.github.io/claude-code-china-guide"
REPO = "https://github.com/code2ai-codes/claude-code-china-guide"
HOME = "https://www.code2ai.codes/"

# 导航顺序 = 读者的实际路径：先跑起来，再出问题才往下查
NAV = [
    ("index.html", "首页"),
    ("getting-started.html", "从零到跑通"),
    ("install.html", "安装"),
    ("configuration.html", "端点配置"),
    ("troubleshooting.html", "排错"),
    ("network-issues.html", "网络问题"),
    ("upgrade.html", "升级"),
    ("third-party-services.html", "接入服务五类"),
]


def gh_slug(text: str) -> str:
    """GitHub 的标题锚点规则：小写、去标点、空格转连字符、中文原样保留。

    必须和 GitHub 一致，否则同一份 markdown 里的锚点链接在仓库页能用、
    在 Pages 上就断了。
    """
    s = re.sub(r"<[^>]+>", "", text).strip().lower()
    s = re.sub(r"[`*\[\]()]", "", s)          # 不动下划线：base_url 这类标识符要原样留着
    s = re.sub(r"[^\w一-鿿 \-]", "", s)
    return s.replace(" ", "-")


def md_files():
    yield ROOT / "README.md", "index.html"
    for f in sorted((ROOT / "docs").glob("*.md")):
        yield f, f.stem + ".html"


def split_title(raw: str):
    lines = raw.split("\n")
    for i, ln in enumerate(lines):
        if ln.startswith("# "):
            return ln[2:].strip(), "\n".join(lines[i + 1:]).lstrip("\n")
    return "", raw


def explicit_desc(raw: str) -> str:
    """md 里可以用 `<!-- description: ... -->` 手写 meta description。

    自动取首段经常抓到链接文字和文件名,对搜索结果里的读者没有意义。
    这段文案同时是 meta description、og:description 和 JSON-LD 的 description,
    是搜索结果里唯一由我们控制的一段字,值得手写。HTML 注释在 GitHub 上不渲染。
    """
    m = re.search(r"<!--\s*description:\s*(.+?)\s*-->", raw, re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def first_para(body: str) -> str:
    """取第一段有实质内容的文字做 meta description（没手写时的回落）。"""
    for block in body.split("\n\n"):
        t = re.sub(r"[*`#>\[\]]|\(([^)]*)\)", "", block).strip()
        t = re.sub(r"\s+", " ", t)
        if len(t) > 40 and not t.startswith(("|", "-", ">", "```")):
            return t[:155]
    return ""


def rewrite_links(md: str) -> str:
    """把仓库内的相对链接改成 Pages 的扁平路径，锚点原样保留。

    `docs/install.md#x` → `install.html#x`     （README 里的写法）
    `install.md#x`      → `install.html#x`     （docs 之间互链的写法）
    """
    def sub(m):
        text, link = m.group(1), m.group(2)
        path, _, frag = link.partition("#")
        if path.startswith(("http://", "https://", "mailto:")):
            return m.group(0)
        name = Path(path).stem
        if not path:                       # 纯锚点，页内跳转
            return f"[{text}](#{frag})"
        return f"[{text}]({name}.html{'#' + frag if frag else ''})"

    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", sub, md)


def extract_faq(body: str):
    """抽 FAQ 段里的问答，用来生成 FAQPage 结构化数据。

    本仓库的写法是 `## FAQ` 下面 `**Q：……**` 加一段答案。
    """
    m = re.search(r"\n##\s*(?:FAQ|常见问题)[^\n]*\n(.*)$", body, re.S)
    if not m:
        return []
    seg = re.split(r"\n##\s", m.group(1))[0]
    out, cur = [], None
    for block in seg.split("\n\n"):
        b = block.strip()
        if not b:
            continue
        q = re.match(r"\*\*Q[：:]\s*(.+?)\*\*\s*(.*)$", b, re.S)
        if q:
            if cur and cur["a"]:
                out.append(cur)
            cur = {"q": q.group(1).strip(),
                   "a": re.sub(r"[*`]", "", q.group(2)).strip()}
        elif cur is not None:
            cur["a"] = (cur["a"] + " " + re.sub(r"[*`]", "", b)).strip()
    if cur and cur["a"]:
        out.append(cur)
    return [f for f in out if f["a"]]


def build_jsonld(title, desc, url, words, faq):
    graph = [
        {
            "@type": "TechArticle",
            "@id": f"{url}#article",
            "headline": title, "name": title, "description": desc,
            "inLanguage": "zh-CN", "url": url, "wordCount": words,
            "datePublished": date.today().isoformat(),
            "dateModified": date.today().isoformat(),
            "mainEntityOfPage": {"@type": "WebPage", "@id": url},
            "author": {"@id": "https://www.code2ai.codes/#organization"},
            "publisher": {"@id": "https://www.code2ai.codes/#organization"},
            "license": "https://opensource.org/licenses/MIT",
        },
        {
            "@type": "Organization",
            "@id": "https://www.code2ai.codes/#organization",
            "name": "Code2AI", "url": HOME,
            "description": "面向国内开发者的 Claude Code 接入网关，域名 code2ai.codes。",
        },
    ]
    if faq:
        graph.append({
            "@type": "FAQPage", "@id": f"{url}#faq",
            "mainEntity": [{"@type": "Question", "name": f["q"],
                            "acceptedAnswer": {"@type": "Answer", "text": f["a"]}}
                           for f in faq],
        })
    return json.dumps({"@context": "https://schema.org", "@graph": graph},
                      ensure_ascii=False, indent=2)


CSS = """
:root{--fg:#1a1a1a;--dim:#57606a;--line:#d8dee4;--bg:#fff;--code:#f6f8fa;--link:#0969da}
*{box-sizing:border-box}
body{margin:0;font:16px/1.75 -apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans CJK SC","PingFang SC","Microsoft YaHei",sans-serif;color:var(--fg);background:var(--bg)}
.wrap{max-width:860px;margin:0 auto;padding:0 20px}
header{border-bottom:1px solid var(--line);margin-bottom:32px}
header .wrap{padding-top:18px;padding-bottom:14px}
.brand{font-weight:600;font-size:15px;text-decoration:none;color:var(--fg)}
.brand span{color:var(--dim);font-weight:400}
nav{margin-top:10px;display:flex;flex-wrap:wrap;gap:6px 16px;font-size:14px}
nav a{color:var(--dim);text-decoration:none}
nav a:hover,nav a.on{color:var(--link)}
nav a.on{font-weight:600}
h1{font-size:30px;line-height:1.35;margin:0 0 20px}
h2{font-size:22px;margin:38px 0 14px;padding-bottom:6px;border-bottom:1px solid var(--line)}
h3{font-size:18px;margin:26px 0 10px}
a{color:var(--link)}
p,li{overflow-wrap:break-word}
code{background:var(--code);padding:.15em .4em;border-radius:4px;font-size:.88em;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
pre{background:var(--code);padding:14px 16px;border-radius:6px;overflow-x:auto;line-height:1.5}
pre code{background:none;padding:0;font-size:13.5px}
table{border-collapse:collapse;width:100%;margin:18px 0;font-size:15px;display:block;overflow-x:auto}
th,td{border:1px solid var(--line);padding:8px 12px;text-align:left;vertical-align:top}
th{background:var(--code);font-weight:600;white-space:nowrap}
blockquote{margin:18px 0;padding:2px 16px;border-left:3px solid var(--line);color:var(--dim)}
footer{margin-top:56px;border-top:1px solid var(--line);padding:20px 0 40px;font-size:14px;color:var(--dim)}
footer a{color:var(--dim)}
@media(max-width:600px){h1{font-size:25px}body{font-size:15.5px}}
"""

PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="article">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
<meta property="og:locale" content="zh_CN">
<style>{css}</style>
<script type="application/ld+json">
{jsonld}
</script>
</head>
<body>
<header><div class="wrap">
<a class="brand" href="{site}/">claude-code-china-guide <span>· Code2AI 维护的开源手册</span></a>
<nav>{nav}</nav>
</div></header>
<main class="wrap">
<h1>{h1}</h1>
{body}
</main>
<footer><div class="wrap">
<p>本手册开源在 <a href="{repo}">GitHub</a>（MIT），欢迎提 issue 和 PR 纠错。
由 <a href="{home}">Code2AI（code2ai.codes）</a> 维护——我们自己做 Claude Code 接入服务，
所以手册里所有验证方法都写成对任何一家都适用的形式，包括拿它来验我们。</p>
</div></footer>
</body>
</html>
"""


def render(md_path: Path, out_name: str, check_only=False):
    raw = md_path.read_text(encoding="utf-8")
    title, body_md = split_title(raw)
    desc = explicit_desc(raw) or first_para(body_md)
    faq = extract_faq(body_md)
    body_md = rewrite_links(body_md)

    md = markdown.Markdown(extensions=["tables", "fenced_code", "toc", "attr_list"],
                           extension_configs={"toc": {"slugify": lambda v, s: gh_slug(v)}})
    body_html = md.convert(body_md)

    url = f"{SITE}/" if out_name == "index.html" else f"{SITE}/{out_name}"
    page_title = title if out_name == "index.html" else f"{title} · claude-code-china-guide"
    nav = "".join(
        f'<a href="{SITE}/{"" if n == "index.html" else n}"'
        f'{" class=\"on\"" if n == out_name else ""}>{html.escape(label)}</a>'
        for n, label in NAV if (ROOT / ("README.md" if n == "index.html" else f"docs/{Path(n).stem}.md")).exists()
    )
    out = PAGE.format(
        title=html.escape(page_title), desc=html.escape(desc), url=url,
        css=CSS, jsonld=build_jsonld(title, desc, url, len(body_md), faq),
        nav=nav, h1=html.escape(title), body=body_html,
        site=SITE, repo=REPO, home=HOME,
    )
    if not check_only:
        (OUT / out_name).write_text(out, encoding="utf-8")
    return out_name, title, desc, len(faq), body_html


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只校验，不写文件")
    a = ap.parse_args()

    if not a.check:
        if OUT.exists():
            shutil.rmtree(OUT)
        OUT.mkdir()

    pages, anchors, links = [], {}, []
    for md_path, out_name in md_files():
        _, title, desc, nfaq, body_html = render(md_path, out_name, a.check)
        pages.append(out_name)
        anchors[out_name] = set(re.findall(r'id="([^"]+)"', body_html))
        for href in re.findall(r'href="([^"]+)"', body_html):
            links.append((out_name, href))
        flag = f"  FAQ×{nfaq}" if nfaq else ""
        print(f"  {out_name:30} {title[:34]:36}{flag}")
        if not desc:
            print(f"     ⚠️ 取不到 meta description")

    # 内链校验：目标文件在不在、锚点对不对得上
    bad = 0
    for src, href in links:
        if href.startswith(("http://", "https://", "mailto:", "#")):
            if href.startswith("#") and href[1:] not in anchors[src]:
                print(f"  ⚠️ {src}: 页内锚点断了 {href}"); bad += 1
            continue
        path, _, frag = href.partition("#")
        if path not in pages:
            print(f"  ❌ {src}: 目标页不存在 {href}"); bad += 1
        elif frag and frag not in anchors[path]:
            print(f"  ⚠️ {src}: 锚点对不上 {href}"); bad += 1

    if a.check:
        print(f"\n校验完毕，链接问题 {bad}")
        return 1 if bad else 0

    today = date.today().isoformat()
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{SITE}/{'' if p == 'index.html' else p}</loc>"
                  f"<lastmod>{today}</lastmod></url>\n" for p in pages)
        + "</urlset>\n", encoding="utf-8")
    (OUT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n", encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")

    print(f"\n✅ {len(pages)} 页 → {OUT}（链接问题 {bad}）")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
