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
    others = [a for a in articles if a["slug"] != current_slug][:3]
    cards = []
    for a in others:
        cards.append(f'''          <article class="column-card reveal">
            <a href="{a["slug"]}.html" class="card-link">
              <div class="card-img-wrap">
                <img src="{a["cardImage"]}" alt="" class="card-img" loading="lazy">
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

def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    articles = data["articles"]
    print(f"Building {len(articles)} articles...")
    for article in articles:
        build_article(article, articles)
    build_sitemap(articles)
    print("Done.")

if __name__ == "__main__":
    main()
