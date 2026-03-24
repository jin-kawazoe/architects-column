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

# Unsplash フォトID（絶対重複使用なし・articles.json全体で管理）
# 全て目視確認済みの高品質建築写真
UNSPLASH_CURATED = [
    # 住宅外観・ミニマル系
    "1523217582562-09d0def993a6",  # 白ミニマルキューブハウス
    "1600585154340-be6161a56a0c",  # ダーク木×白モダン外観（夕暮れ）
    "1600585154526-990dced4db0d",  # ダーク建築外観（夜）
    "1613977257363-707ba9348227",  # 白モダンヴィラ+プール
    "1580587771525-78b9dba3b914",  # モダンヴィラ+プール
    "1600047509807-ba8f99d2cdde",  # 木パネルモダン外観
    "1583608205776-bfd35f0d9f83",  # オープン住宅+プール
    "1600596542815-ffad4c1539a9",  # 白モダンヴィラ
    "1631679706909-1844bbd07221",  # 木エントランス外観
    "1568605114967-8130f3a36994",  # 木造住宅（夜）
    "1512917774080-9991f1c4c750",  # ガラス張りヴィラ
    # インテリア・空間系
    "1600573472591-ee6b68d14c68",  # 建築的ベッドルーム
    "1600607687939-ce8a6c25118c",  # 白ミニマル寝室
    "1556909114-f6e7ad7d3136",     # モダンリビング
    "1618221195710-dd6b41faaea6",  # ミニマルインテリア
    "1586023492125-27b2c045efd3",  # ホワイトインテリア
    "1555041469-db61197e5b50",     # コンクリートインテリア
    # 都市・建築外観系
    "1486325212027-8081e485255e",  # 都市スカイライン
    "1567684014761-b65e2e59b9eb",  # ガラス集合住宅（夕暮れ）
    "1486718448742-163732cd1544",  # 建築的コリドー
    "1431576901776-e539bd916ba2",  # ガラス建築外観
    "1519971559892-e4e55a4f04b3",  # モダン商業建築
    "1479839672679-a46cb8676de8",  # 建築ディテール
    "1543286386-713bdd548da4",     # 都市の建築群
    # 素材・ディテール系
    "1558618666-fcd25c85cd64",     # コンクリートテクスチャー
    "1497366216548-37526070297c",  # モダンオフィス空間
    "1600210492486-724a01aed8b8",  # ミニマル建築外観
    "1449824913935-59a10b8d2000",  # 夜の都市建築
    "1460317442991-0ec209397118",  # 建築廊下
    "1504307651254-35680f356dfd",  # 建築コンクリート
]


def get_used_photo_ids():
    """articles.jsonから使用済み画像IDを全て取得する（Unsplash・Pexels両対応）"""
    if not ARTICLES_JSON.exists():
        return set()
    with open(ARTICLES_JSON, encoding="utf-8") as f:
        data = json.load(f)
    used = set()
    for a in data.get("articles", []):
        for key in ("heroImage", "cardImage"):
            url = a.get(key, "")
            # Unsplash形式: /photo-{ID}?
            m = re.search(r"unsplash\.com/photo-([\w-]+)", url)
            if m:
                used.add(m.group(1))
            # Pexels形式: /photos/{ID}/
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
  "title": "記事タイトル（20〜30文字以内、端的で印象的なもの。長すぎない）",
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
    for pid in UNSPLASH_CURATED:
        if pid not in used:
            return pid
    # 全て使用済みの場合は最初に戻す（プールを追加すべきタイミング）
    print("[WARNING] 全画像IDが使用済みです。プールに画像を追加してください。")
    return UNSPLASH_CURATED[0]


def add_to_articles_json(meta, cat, today_str, state):
    """articles.jsonに新記事を追加"""
    with open(ARTICLES_JSON, encoding="utf-8") as f:
        data = json.load(f)

    photo_id = pick_photo_id()
    hero_image = f"https://images.unsplash.com/photo-{photo_id}?auto=format&fit=crop&w=1600&h=900&q=80"
    card_image = f"https://images.unsplash.com/photo-{photo_id}?auto=format&fit=crop&w=600&h=400&q=80"

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
