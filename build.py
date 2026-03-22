#!/usr/bin/env python3
"""KAWAZOE-ARCHITECTS Article Build System"""
import json, re
from pathlib import Path
import markdown
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor
from markdown.preprocessors import Preprocessor

BASE     = Path(__file__).parent
CONTENT  = BASE / "content"
OUT      = BASE / "articles"
DATA     = BASE / "articles.json"
TEMPLATE = BASE / "article.html"

# H2 に id を振り、TOC リストを作る
class _HC(Treeprocessor):
    def __init__(self, md, toc):
        super().__init__(md); self.toc = toc; self.n = 0
    def run(self, root):
        for el in root.iter():
            if el.tag == "h2":
                self.n += 1; sid = f"section{self.n}"; el.set("id", sid)
                self.toc.append({"id": sid, "text": "".join(el.itertext())})

class HCExt(Extension):
    def __init__(self, toc, **kw): self.toc = toc; super().__init__(**kw)
    def extendMarkdown(self, md):
        md.treeprocessors.register(_HC(md, self.toc), "hc", 15)

# :::callout ... ::: -> <div class="article-callout">
class _CP(Preprocessor):
    def run(self, lines):
        out, buf, inside = [], [], False
        for ln in lines:
            if ln.strip() == ":::callout": inside, buf = True, []
            elif ln.strip() == ":::" and inside:
                inside = False; t = chr(10).join(buf).strip()
                out += ["", f'<div class="article-callout"><span class="callout-icon">&#8594;</span><p>{t}</p></div>', ""]
            elif inside: buf.append(ln)
            else: out.append(ln)
        return out

class CPExt(Extension):
    def extendMarkdown(self, md):
        md.preprocessors.register(_CP(md), "co", 30)

# ![alt](url) {caption: text} -> <figure>
class _IC(Preprocessor):
    PAT = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)\s*\{caption:\s*(.*?)\}')
    def run(self, lines):
        out = []
        for ln in lines:
            m = self.PAT.match(ln.strip())
            if m:
                alt, src, cap = m.group(1), m.group(2), m.group(3)
                out += ["",
                        '<figure class="article-figure">',
                        f'  <img src="{src}" alt="{alt}" loading="lazy">',
                        f'  <figcaption>{cap}</figcaption>',
                        '</figure>', ""]
            else:
                out.append(ln)
        return out

class ICExt(Extension):
    def extendMarkdown(self, md):
        md.preprocessors.register(_IC(md), "ic", 35)

def count_words(text):
    """日本語・英語混在テキストの語数/文字数を推定"""
    # マークダウン記号を除去
    clean = re.sub(r'[#*`_~\[\]()!>:|-]', ' ', text)
    clean = re.sub(r'https?://\S+', '', clean)
    # 日本語文字数 + 英語単語数
    ja_chars = len(re.findall(r'[\u3000-\u9fff\uff00-\uffef]', clean))
    en_words = len(re.findall(r'[a-zA-Z]+', clean))
    # 日本語は1文字≒0.5語(読み速度換算)、英語は1語
    return ja_chars + en_words

def md_to_html(text):
    toc = []
    md = markdown.Markdown(
        extensions=[HCExt(toc), CPExt(), ICExt(), "extra"],
        output_format="html"
    )
    body = md.convert(text)
    body = body.replace("<p>", '<p class="article-lead">', 1)
    body = body.replace("<blockquote>", '<blockquote class="article-quote">')
    return body, toc

def toc_html(items):
    lines = []
    for i, item in enumerate(items):
        cls = "toc-link active" if i == 0 else "toc-link"
        lines.append(f'<a href="#{item["id"]}" class="{cls}">{item["text"]}</a>')
    return "\n            ".join(lines)

def tags_html(tags):
    return "\n          ".join(f'<span class="tag-item">{t}</span>' for t in tags)

def related_html(articles, current_slug):
    current = next((a for a in articles if a["slug"] == current_slug), None)
    current_cat = current["categoryLabel"] if current else ""
    others = [a for a in articles if a["slug"] != current_slug]
    same_cat = [a for a in others if a["categoryLabel"] == current_cat][:3]
    diff_cat = [a for a in others if a["categoryLabel"] != current_cat]
    picks = (same_cat + diff_cat)[:3]
    cards = []
    for a in picks:
        safe_title = a["title"].replace('"', "&quot;")
        cards.append(f'''          <article class="column-card reveal">
            <a href="{a["slug"]}.html" class="card-link">
              <div class="card-img-wrap">
                <img src="{a["cardImage"]}" alt="{safe_title}" class="card-img" loading="lazy">
                <span class="card-tag">{a["categoryLabel"]}</span>
              </div>
              <div class="card-body">
                <h3 class="card-title">{a["title"]}</h3>
                <div class="card-meta">
                  <span class="card-author">{a["author"]["name"]}</span>
                  <span class="card-date">{a["dateFormatted"]}</span>
                </div>
              </div>
            </a>
          </article>''')
    return "\n".join(cards)

def build_article(article, all_articles):
    slug = article["slug"]
    md_path = CONTENT / f"{slug}.md"
    if not md_path.exists():
        print(f"  skip: {slug} (no .md file)")
        return

    text = md_path.read_text(encoding="utf-8")
    body_html, toc = md_to_html(text)
    word_count = count_words(text)
    template = TEMPLATE.read_text(encoding="utf-8")

    replacements = {
        "[[SLUG]]":             slug,
        "[[TITLE]]":            article["title"],
        "[[TITLE_HTML]]":       article["titleHtml"],
        "[[DESCRIPTION]]":      article["excerpt"],
        "[[DATE_ISO]]":         article["date"],
        "[[DATE_FORMATTED]]":   article["dateFormatted"],
        "[[CATEGORY]]":         article["category"],
        "[[CATEGORY_LABEL]]":   article["categoryLabel"],
        "[[HERO_IMAGE]]":       article["heroImage"],
        "[[READ_TIME]]":        article["readTime"],
        "[[AUTHOR_NAME]]":      article["author"]["name"],
        "[[AUTHOR_ROLE]]":      article["author"]["role"],
        "[[AUTHOR_AVATAR]]":    article["author"]["avatarChar"],
        "[[AUTHOR_AVATAR_IMG]]": (
            f'<img src="../img/{article["author"]["avatarImage"]}" alt="{article["author"]["name"]}" class="author-avatar-img">'
            if article["author"].get("avatarImage")
            else article["author"].get("avatarChar", "")
        ),
        "[[AUTHOR_BIO]]":       article["author"]["bio"],
        "[[ARTICLE_BODY]]":     body_html,
        "[[TOC_ITEMS]]":        toc_html(toc),
        "[[TAGS]]":             tags_html(article["tags"]),
        "[[RELATED_ARTICLES]]": related_html(all_articles, slug),
        "[[KEYWORDS]]":         article["keywords"],
        "[[CTA_TITLE]]":        article.get("ctaTitle", "住まいづくりについて、<br>建築家に相談してみませんか。"),
        "[[CTA_TEXT]]":         article.get("ctaText", "敷地のこと、予算のこと、漠然とした理想のこと。どんな段階でも、まずはお気軽にご相談ください。"),
        "[[ARTICLE_FAQ_JSON_LD]]": faq_json_ld(article.get("faqItems", [])),
        "[[WORD_COUNT]]":        str(word_count),
    }

    html = template
    for key, val in replacements.items():
        html = html.replace(key, val)

    OUT.mkdir(exist_ok=True)
    out_path = OUT / f"{slug}.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"  built: articles/{slug}.html")

def faq_json_ld(faq_items):
    if not faq_items:
        return ""
    entities = [
        {
            "@type": "Question",
            "name": item["q"],
            "acceptedAnswer": {"@type": "Answer", "text": item["a"]}
        }
        for item in faq_items
    ]
    data = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": entities}
    return f'<script type="application/ld+json">\n  {json.dumps(data, ensure_ascii=False, indent=2)}\n  </script>'

def build_sitemap(articles):
    import datetime
    today = datetime.date.today().isoformat()
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
        '        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">',
        '  <url>',
        '    <loc>https://kawazoe-architects.com/column/</loc>',
        f'    <lastmod>{today}</lastmod>',
        '    <changefreq>daily</changefreq>',
        '    <priority>1.0</priority>',
        '  </url>',
    ]
    for a in articles:
        hero = a.get("heroImage", "")
        title = a.get("title", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        lines += [
            '  <url>',
            f'    <loc>https://kawazoe-architects.com/column/articles/{a["slug"]}.html</loc>',
            f'    <lastmod>{a["date"]}</lastmod>',
            '    <changefreq>monthly</changefreq>',
            '    <priority>0.8</priority>',
        ]
        if hero:
            lines += [
                '    <image:image>',
                f'      <image:loc>{hero.split("?")[0]}</image:loc>',
                f'      <image:title>{title}</image:title>',
                '    </image:image>',
            ]
        lines.append('  </url>')
    lines.append('</urlset>')
    (BASE / "sitemap.xml").write_text("\n".join(lines), encoding="utf-8")
    print("  built: sitemap.xml")

def build_category_pages(articles):
    """カテゴリ別ページを生成"""
    categories = {}
    for a in articles:
        label = a["categoryLabel"]
        categories.setdefault(label, []).append(a)

    index_template = (BASE / "index.html").read_text(encoding="utf-8")

    for label, cat_articles in categories.items():
        slug_map = {
            "住宅設計": "housing", "建築論": "architecture",
            "素材研究": "materials", "都市と暮らし": "urban", "商業建築": "commercial"
        }
        cat_slug = slug_map.get(label, label)
        cards_html = ""
        for a in cat_articles:
            safe_title = a["title"].replace('"', "&quot;")
            cards_html += f'''        <article class="column-card reveal">
          <a href="articles/{a["slug"]}.html" class="card-link">
            <div class="card-img-wrap">
              <img src="{a["cardImage"]}" alt="{safe_title}" class="card-img" loading="lazy">
              <span class="card-tag">{a["categoryLabel"]}</span>
            </div>
            <div class="card-body">
              <h3 class="card-title">{a["title"]}</h3>
              <p class="card-excerpt">{a["excerpt"]}</p>
              <div class="card-meta">
                <span class="card-author">{a["author"]["name"]}</span>
                <span class="card-date">{a["dateFormatted"]}</span>
              </div>
            </div>
          </a>
        </article>\n'''

        html = f'''<!DOCTYPE html>
<html lang="ja">
<head>
  <script>(function(w,d,s,l,i){{w[l]=w[l]||[];w[l].push({{'gtm.start':new Date().getTime(),event:'gtm.js'}});var f=d.getElementsByTagName(s)[0],j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src='https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);}})(window,document,'script','dataLayer','GTM-PV96M93');</script>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{label} — KAWAZOE-ARCHITECTS コラム</title>
  <meta name="description" content="{label}に関する建築コラム一覧。河添建築事務所の建築家・河添甚が執筆する専門的な建築知識をお届けします。">
  <link rel="canonical" href="https://kawazoe-architects.com/column/category/{cat_slug}.html">
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;1,300;1,400&family=Noto+Sans+JP:wght@300;400;500&family=Inter:wght@300;400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="../css/style.css?v=2">
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"CollectionPage","name":"{label} — KAWAZOE-ARCHITECTS コラム","url":"https://kawazoe-architects.com/column/category/{cat_slug}.html","description":"{label}に関する建築コラム一覧"}}
  </script>
</head>
<body>
<noscript><iframe src="https://www.googletagmanager.com/ns.html?id=GTM-PV96M93" height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>
  <header class="header" id="header">
    <div class="header-inner">
      <a href="../index.html" class="logo">
        <img src="../logo.png" alt="KAWAZOE-ARCHITECTS" class="logo-img logo-img--light">
        <img src="../logo_black.png" alt="KAWAZOE-ARCHITECTS" class="logo-img logo-img--dark">
      </a>
      <nav class="nav">
        <a href="../index.html" class="nav-link">コラム</a>
        <a href="https://kawazoe-architects.com/project/project.html" class="nav-link">プロジェクト</a>
        <a href="https://kawazoe-architects.com/about-us/about-us.html" class="nav-link">事務所について</a>
        <a href="https://www.kawazoe-architects.com/inquiry/" class="nav-link">お問い合わせ</a>
      </nav>
      <div class="header-actions">
        <button class="theme-toggle" id="themeToggle" aria-label="テーマ切替"><span class="theme-icon">◐</span></button>
        <button class="menu-toggle" id="menuToggle" aria-label="メニュー"><span></span><span></span><span></span></button>
      </div>
    </div>
  </header>
  <main style="padding-top:80px">
    <div class="container" style="max-width:1200px;margin:0 auto;padding:40px 24px">
      <div class="breadcrumb" style="margin-bottom:32px">
        <a href="../index.html">コラム</a> / <span>{label}</span>
      </div>
      <h1 style="font-size:2rem;margin-bottom:8px">{label}</h1>
      <p style="color:var(--text-muted);margin-bottom:48px">{len(cat_articles)}本の記事</p>
      <div class="columns-grid">
{cards_html}      </div>
    </div>
  </main>
  <footer class="footer">
    <div class="footer-inner">
      <div class="footer-bottom">
        <span class="footer-copy">© 2026 KAWAZOE-ARCHITECTS. All rights reserved.</span>
      </div>
    </div>
  </footer>
  <script src="../js/main.js"></script>
</body>
</html>'''
        cat_dir = BASE / "category"
        cat_dir.mkdir(exist_ok=True)
        out_path = cat_dir / f"{cat_slug}.html"
        out_path.write_text(html, encoding="utf-8")
        print(f"  built: category/{cat_slug}.html ({len(cat_articles)}件)")


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    articles = data["articles"]
    print(f"Building {len(articles)} articles...")
    for article in articles:
        build_article(article, articles)
    build_category_pages(articles)
    build_sitemap(articles)
    print("Done.")

if __name__ == "__main__":
    main()
