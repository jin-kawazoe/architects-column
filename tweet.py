"""
X (Twitter) 自動投稿スクリプト
毎朝タスクスケジューラから実行する
"""
import json
import sys
import tweepy
from pathlib import Path
from tweet_config import API_KEY, API_KEY_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET

# Windows コンソールの文字コード対策
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path(__file__).parent
ARTICLES_JSON = BASE / "articles.json"
STATE_FILE = BASE / "tweet_state.json"
SITE_URL = "https://kawazoe-architects.com/column"

# カテゴリ別ハッシュタグ
HASHTAGS = {
    "住宅設計": "#住宅設計 #建築家 #注文住宅",
    "建築論":   "#建築論 #建築家 #設計",
    "素材研究": "#建築素材 #建築家 #素材",
    "都市と暮らし": "#都市 #まちづくり #建築家",
    "商業建築": "#商業建築 #店舗設計 #建築家",
}

# カテゴリローテーション順
CATEGORY_ORDER = ["住宅設計", "建築論", "素材研究", "都市と暮らし", "商業建築"]


def load_articles():
    with open(ARTICLES_JSON, encoding="utf-8") as f:
        data = json.load(f)
    return data["articles"]


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"tweeted_slugs": [], "last_category_index": -1}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def pick_next_article(articles, state):
    tweeted = set(state.get("tweeted_slugs", []))
    last_cat_idx = state.get("last_category_index", -1)

    # カテゴリを順番にローテーション
    for i in range(len(CATEGORY_ORDER)):
        cat_idx = (last_cat_idx + 1 + i) % len(CATEGORY_ORDER)
        category = CATEGORY_ORDER[cat_idx]

        # このカテゴリで未投稿の記事を探す
        candidates = [
            a for a in articles
            if a.get("categoryLabel") == category and a["slug"] not in tweeted
        ]

        if candidates:
            return candidates[0], cat_idx

    # 全記事投稿済みの場合はリセット
    print("全記事を投稿済み。リセットして最初から再開します。")
    state["tweeted_slugs"] = []
    save_state(state)
    return pick_next_article(articles, state)


def format_tweet(article):
    title = article["title"]
    excerpt = article.get("excerpt", "")
    slug = article["slug"]
    category_label = article.get("categoryLabel", "住宅設計")
    hashtags = HASHTAGS.get(category_label, "#建築家 #住宅設計")

    url = f"{SITE_URL}/articles/{slug}.html"

    # ツイート本文（280文字以内）
    # URLはTwitterが23文字にカウントするため実質的な上限は余裕あり
    tweet = f"{title}\n\n{excerpt[:80]}…\n\n{url}\n\n{hashtags}"

    return tweet


def post_tweet(text):
    client = tweepy.Client(
        consumer_key=API_KEY,
        consumer_secret=API_KEY_SECRET,
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_TOKEN_SECRET,
    )
    response = client.create_tweet(text=text, user_auth=True)
    return response


def main():
    articles = load_articles()
    state = load_state()

    article, cat_idx = pick_next_article(articles, state)

    tweet_text = format_tweet(article)
    print("投稿内容:")
    print("-" * 60)
    print(tweet_text)
    print("-" * 60)
    print(f"文字数: {len(tweet_text)}")

    response = post_tweet(tweet_text)
    print(f"投稿成功: tweet_id={response.data['id']}")

    # 状態を更新
    state["tweeted_slugs"].append(article["slug"])
    state["last_category_index"] = cat_idx
    save_state(state)

    print(f"記事「{article['title']}」を投稿しました。")


if __name__ == "__main__":
    main()
