"""
記事自動生成スクリプト
毎日タスクスケジューラから実行する
Anthropic Claude API を使って記事を自動生成し、articles.json と content/ に追加する
"""
import os
import json
import sys
import re
import datetime
import anthropic
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path(__file__).parent
ARTICLES_JSON = BASE / "articles.json"
CONTENT_DIR = BASE / "content"
STATE_FILE = BASE / "gen_state.json"

# カテゴリローテーション
CATEGORIES = [
    {
        "category": "住宅",
        "categoryLabel": "住宅設計",
        "hashtags": "#住宅設計 #建築家 #注文住宅",
        "themes": [
            "二世帯住宅の設計——家族の距離感を建築で解く",
            "中庭のある家——光と風と暮らしの関係",
            "土間のある住まい——内と外をつなぐ空間の再考",
            "吹き抜けと開放感——縦方向の空間設計論",
            "シニア世代の住まいリフォーム——老後を見据えた空間",
            "趣味室のある家——個人の場所と家族の場所を設計する",
            "共働き世帯の家事動線——時短設計の考え方",
            "書斎と在宅ワーク——仕事と暮らしが共存する住まい",
        ]
    },
    {
        "category": "論考",
        "categoryLabel": "建築論",
        "hashtags": "#建築論 #建築家 #設計",
        "themes": [
            "建築と記憶——場所が持つ時間の厚み",
            "スケールと身体——建築が人の感覚に与える影響",
            "余白の設計——何も置かないことの豊かさ",
            "建築における透明性——ガラスが変えた空間の概念",
            "地産地消の建築——地域素材が生む固有性",
            "静寂の建築——音環境をデザインするということ",
            "模型が考える——設計プロセスにおける手の知性",
        ]
    },
    {
        "category": "素材",
        "categoryLabel": "素材研究",
        "hashtags": "#建築素材 #建築家 #素材",
        "themes": [
            "タイルの表情——床と壁が語る建築の個性",
            "鉄の細工——建築における金属の表現",
            "石の重さ——石材が持つ時間と空間の重力",
            "和紙と光——透過素材が演出する柔らかな境界",
            "テラゾーの復権——集合素材が見せる現代性",
            "錆と美——コールテン鋼の経年変化論",
        ]
    },
    {
        "category": "都市",
        "categoryLabel": "都市と暮らし",
        "hashtags": "#都市 #まちづくり #建築家",
        "themes": [
            "高密度都市と緑——東京の中の自然を考える",
            "公共空間のデザイン——誰のための広場か",
            "商店街の空洞化——まちの記憶をどう継ぐか",
            "郊外住宅地の未来——ベッドタウンの次のかたち",
            "水辺と建築——川や港が変えるまちの顔",
        ]
    },
    {
        "category": "商業建築",
        "categoryLabel": "商業建築",
        "hashtags": "#商業建築 #店舗設計 #建築家",
        "themes": [
            "飲食店の設計——厨房と客席の距離感が生む体験",
            "美容室・サロンの空間設計——非日常を演出する場",
            "ホテルロビーの建築論——到着の体験をデザインする",
            "医療施設の設計——安心と清潔さを空間で伝える",
            "保育施設の建築——子どもの身体尺度で設計する",
        ]
    },
]

AUTHOR = {
    "name": "河添 甚",
    "role": "代表建築家 / KAWAZOE-ARCHITECTS主宰",
    "avatarChar": "河",
    "bio": "1977年、香川県生まれ。2002年に大阪工業大学工学部建築学科を卒業。2010年、河添建築事務所に参画し代表に就任。香川・東京の二拠点を構え、住宅から商業建築まで幅広い設計を手がける。",
    "avatarImage": "avatar.jpg"
}

# Pexels フォトID（カテゴリ別の厳選画像プール）
# 目視確認済みの建築・インテリア良質画像プール（絶対に重複使用しない）
PEXELS_CURATED = [
    "1571460",  # モダンリビング・フローティング階段
    "1571458",  # ミニマルリビング・階段
    "1571455",  # キッチン+ダイニング+階段
    "1571456",  # 広々とした開放的リビング
    "1571457",  # リビング+暖炉・上質な内装
    "1643384",  # モダンキッチン・木+白
    "280222",   # 大きな住宅外観・芝生
    "4352247",  # ミニマルな白いソファ
    "2724748",  # モダンホワイトキッチン
    "2187605",  # 日本の古民家集落・屋根
    "2187603",  # 日本の古民家・夕暮れ光
    "2507010",  # ハイライズビルロビー・広大な空間
    "2079234",  # モダンアパートビル外観
    "2041627",  # オフィス俯瞰・ミーティングテーブル
    "1571461",  # ホワイトミニマル浴室
    "1571462",  # ホワイトミニマルシャワー
    "5872379",  # グレータイル+光の影（素材感）
]


def get_used_photo_ids():
    """articles.jsonから使用済み画像IDを全て取得する"""
    if not ARTICLES_JSON.exists():
        return set()
    with open(ARTICLES_JSON, encoding="utf-8") as f:
        data = json.load(f)
    used = set()
    for a in data.get("articles", []):
        for key in ("heroImage", "cardImage"):
            url = a.get(key, "")
            m = re.search(r"/photos/(\d+)/", url)
            if m:
                used.add(m.group(1))
    return used


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"last_category_index": -1, "used_themes": {}, "used_photo_indices": {}}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def pick_theme(state):
    last_idx = state.get("last_category_index", -1)
    used_themes = state.get("used_themes", {})

    # カテゴリをローテーション
    for i in range(len(CATEGORIES)):
        cat_idx = (last_idx + 1 + i) % len(CATEGORIES)
        cat = CATEGORIES[cat_idx]
        label = cat["categoryLabel"]
        used = used_themes.get(label, [])
        remaining = [t for t in cat["themes"] if t not in used]

        if remaining:
            theme = remaining[0]
            return cat, theme, cat_idx

    # 全テーマ使用済みの場合リセット
    print("全テーマを使用済み。リセットします。")
    state["used_themes"] = {}
    save_state(state)
    return pick_theme(state)


try:
    from secrets import ANTHROPIC_API_KEY
except ImportError:
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


def generate_article_content(cat, theme):
    """Claude APIで記事を生成する"""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    prompt = f"""あなたは建築家・河添甚（KAWAZOE-ARCHITECTS代表）として、建築コラムを執筆してください。

テーマ: {theme}
カテゴリ: {cat["categoryLabel"]}

以下の形式でMarkdownを出力してください（フロントマターなし、本文のみ）：

要件：
- 2000〜2800文字程度の本格的な建築コラム
- H2見出しを4〜6個使う
- 建築家としての実務経験に基づく具体的な視点
- 専門的すぎず、住宅を検討している一般の方にも読みやすい文体
- 「私は」「私が」など一人称を適度に使い、建築家の個性を出す
- 最後に読者への問いかけや示唆で締める
- 絶対に「まとめ」「おわりに」というH2は使わない

必ず本文のみ出力し、説明や前置きは一切不要です。"""

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


def generate_metadata(cat, theme, body_text):
    """タイトル・excerpt・slug・タグを生成"""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    prompt = f"""以下の建築コラム本文に対して、JSONでメタデータを生成してください。

テーマ: {theme}
カテゴリ: {cat["categoryLabel"]}

本文の冒頭200文字:
{body_text[:200]}

出力形式（JSONのみ、説明不要）:
{{
  "title": "記事タイトル（30〜45文字、ダッシュや副題を含む魅力的なもの）",
  "titleHtml": "タイトルHTML（<br>と<em>で改行・強調）",
  "slug": "英数字とハイフンのみのURL用スラッグ（例: wood-and-space）",
  "excerpt": "記事の要約（80〜100文字、読者の興味を引く）",
  "tags": ["タグ1", "タグ2", "タグ3", "タグ4", "タグ5"],
  "keywords": "キーワード1,キーワード2,キーワード3,キーワード4,キーワード5",
  "readTime": "8 min",
  "ctaTitle": "CTA見出し（30文字以内、<br>で改行）",
  "ctaText": "CTAテキスト（60〜80文字）",
  "faqItems": [
    {{"q": "よくある質問1", "a": "回答1（100文字程度）"}},
    {{"q": "よくある質問2", "a": "回答2（100文字程度）"}}
  ]
}}"""

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = message.content[0].text
    # JSONを抽出
    match = re.search(r'\{[\s\S]+\}', raw)
    if match:
        return json.loads(match.group())
    raise ValueError("メタデータのJSON抽出に失敗: " + raw[:200])


def pick_photo_id():
    """articles.jsonの全使用済みIDを確認し、未使用の画像IDを返す（絶対重複なし）"""
    used = get_used_photo_ids()
    for pid in PEXELS_CURATED:
        if pid not in used:
            return pid
    # 全て使用済みの場合は最初に戻す（プールを追加すべきタイミング）
    print("[WARNING] 全画像IDが使用済みです。プールに画像を追加してください。")
    return PEXELS_CURATED[0]


def add_to_articles_json(meta, cat, today_str, state):
    """articles.jsonに新記事を追加"""
    with open(ARTICLES_JSON, encoding="utf-8") as f:
        data = json.load(f)

    photo_id = pick_photo_id()
    hero_image = f"https://images.pexels.com/photos/{photo_id}/pexels-photo-{photo_id}.jpeg?auto=compress&cs=tinysrgb&w=1600&h=900&fit=crop"
    card_image = f"https://images.pexels.com/photos/{photo_id}/pexels-photo-{photo_id}.jpeg?auto=compress&cs=tinysrgb&w=600&h=400&fit=crop"

    new_article = {
        "slug": meta["slug"],
        "title": meta["title"],
        "titleHtml": meta["titleHtml"],
        "date": today_str,
        "dateFormatted": today_str.replace("-", "."),
        "category": cat["category"],
        "categoryLabel": cat["categoryLabel"],
        "author": AUTHOR,
        "excerpt": meta["excerpt"],
        "heroImage": hero_image,
        "cardImage": card_image,
        "readTime": meta["readTime"],
        "tags": meta["tags"],
        "keywords": meta["keywords"],
        "faqItems": meta["faqItems"],
        "ctaTitle": meta["ctaTitle"],
        "ctaText": meta["ctaText"],
        "cardLayout": "",
        "featured": False
    }

    # 先頭に追加（最新記事を先頭に）
    data["articles"].insert(0, new_article)

    with open(ARTICLES_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"  articles.json に追加: {meta['slug']}")
    return new_article


def main():
    state = load_state()
    cat, theme, cat_idx = pick_theme(state)
    today = datetime.date.today().isoformat()

    print(f"カテゴリ: {cat['categoryLabel']}")
    print(f"テーマ: {theme}")
    print("記事生成中...")

    body_text = generate_article_content(cat, theme)
    print(f"本文生成完了（{len(body_text)}文字）")

    print("メタデータ生成中...")
    meta = generate_metadata(cat, theme, body_text)
    print(f"タイトル: {meta['title']}")
    print(f"スラッグ: {meta['slug']}")

    # Markdownファイル保存
    md_path = CONTENT_DIR / f"{meta['slug']}.md"
    md_path.write_text(body_text, encoding="utf-8")
    print(f"  content/{meta['slug']}.md を保存")

    # articles.jsonに追加
    add_to_articles_json(meta, cat, today, state)

    # 状態更新
    used = state.get("used_themes", {})
    label = cat["categoryLabel"]
    if label not in used:
        used[label] = []
    used[label].append(theme)
    state["used_themes"] = used
    state["last_category_index"] = cat_idx
    save_state(state)

    print(f"\n完了: {meta['title']}")


if __name__ == "__main__":
    main()
