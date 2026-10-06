#!/usr/bin/env python3
"""Reddit API utility for fetching top/hot posts from subreddits, or a single post by URL/ID.

Usage:
    python tools/reddit_api.py top ClaudeAI --period day --limit 10
    python tools/reddit_api.py top ClaudeAI LocalLLaMA SideProject --period day --limit 5
    python tools/reddit_api.py hot ClaudeAI --limit 10
    python tools/reddit_api.py top ClaudeAI --period week --limit 20 --out Temp/data/reddit_claudeai.json

    python tools/reddit_api.py post https://www.reddit.com/r/ClaudeAI/s/THfwKWj3w0
    python tools/reddit_api.py post https://www.reddit.com/r/ClaudeAI/comments/1sw4zmj/title/
    python tools/reddit_api.py post 1sw4zmj --limit 20

Reads REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET from .env file in project root.
Uses OAuth2 client credentials (script app type). No user login needed.
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
import urllib.parse
import base64
from datetime import datetime, timezone, timedelta
from pathlib import Path

USER_AGENT = "RedScrapper/1.0 (personal use script)"

def load_env():
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

def get_access_token():
    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("Error: REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET must be set in .env", file=sys.stderr)
        sys.exit(1)

    auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    data = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode()

    req = urllib.request.Request(
        "https://www.reddit.com/api/v1/access_token",
        data=data,
        headers={
            "Authorization": f"Basic {auth}",
            "User-Agent": USER_AGENT,
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode())
            return body["access_token"]
    except urllib.error.HTTPError as e:
        print(f"Error getting Reddit token: {e.code} {e.reason}", file=sys.stderr)
        try:
            print(e.read().decode(), file=sys.stderr)
        except Exception:
            pass
        sys.exit(1)

def fetch_subreddit(token, subreddit, sort="top", period="day", limit=10):
    params = {"limit": min(limit, 100), "raw_json": 1}
    if sort == "top":
        params["t"] = period

    url = f"https://oauth.reddit.com/r/{subreddit}/{sort}?{urllib.parse.urlencode(params)}"

    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": USER_AGENT,
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"Error fetching r/{subreddit}: {e.code} {e.reason}", file=sys.stderr)
        return None

def resolve_short_url(url):
    """Follow the redirect on a Reddit /s/ short URL to get the canonical /comments/ URL."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.url
    except urllib.error.HTTPError as e:
        return e.headers.get("Location") or url

def extract_post_id(target):
    """Resolve a Reddit URL or bare post ID to a post ID (e.g. '1sw4zmj')."""
    target = target.strip()
    if "/" not in target and " " not in target:
        return target
    if "/s/" in target:
        target = resolve_short_url(target)
    if "/comments/" in target:
        return target.split("/comments/")[1].split("/")[0]
    raise ValueError(f"Could not extract post id from: {target}")

def fetch_post(token, post_id, comment_limit=10):
    url = f"https://oauth.reddit.com/comments/{post_id}?raw_json=1&limit={comment_limit}"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}", "User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())

def print_post(raw, comment_limit=10):
    post = raw[0]["data"]["children"][0]["data"]
    comments = raw[1]["data"]["children"]

    print("=" * 60)
    flair = f" [{post.get('link_flair_text')}]" if post.get("link_flair_text") else ""
    print(f"r/{post['subreddit']}{flair}")
    print(f"Title: {post['title']}")
    print(f"Author: u/{post.get('author', '?')}")
    print(f"Score: {post['score']} | Comments: {post['num_comments']} | Ratio: {post.get('upvote_ratio', 0):.2f}")
    print(f"URL: https://reddit.com{post['permalink']}")
    print("=" * 60)
    if post.get("is_self") and post.get("selftext"):
        print("\nBODY:")
        print(post["selftext"][:6000])
    elif post.get("url"):
        print(f"\nLINK: {post['url']}")

    print("\n" + "=" * 60)
    print(f"TOP {comment_limit} COMMENTS:")
    print("=" * 60)
    shown = 0
    for c in comments:
        if c.get("kind") != "t1" or shown >= comment_limit:
            continue
        d = c["data"]
        body = (d.get("body") or "").strip()
        if not body or body == "[deleted]":
            continue
        print(f"\n--- u/{d.get('author', '?')} ({d.get('score', 0)} pts) ---")
        print(body[:2000])
        shown += 1

def format_post(post):
    d = post["data"]
    created = datetime.fromtimestamp(d["created_utc"], tz=timezone.utc)
    age_h = (datetime.now(timezone.utc) - created).total_seconds() / 3600

    result = {
        "subreddit": d["subreddit"],
        "title": d["title"],
        "author": d.get("author", "[deleted]"),
        "score": d["score"],
        "upvote_ratio": d.get("upvote_ratio", 0),
        "num_comments": d["num_comments"],
        "created_utc": d["created_utc"],
        "created_at": created.strftime("%Y-%m-%d %H:%M UTC"),
        "age_hours": round(age_h, 1),
        "url": d.get("url", ""),
        "permalink": f"https://reddit.com{d['permalink']}",
        "selftext": d.get("selftext", "")[:500] if d.get("is_self") else "",
        "link_flair_text": d.get("link_flair_text", ""),
        "is_self": d.get("is_self", False),
    }
    return result

def print_summary(posts, subreddit):
    if not posts:
        print(f"  r/{subreddit}: no posts found")
        return

    print(f"\nr/{subreddit} — {len(posts)} posts:")
    for i, p in enumerate(posts, 1):
        score = p["score"]
        comments = p["num_comments"]
        age = p["age_hours"]
        title = p["title"][:100]
        flair = f" [{p['link_flair_text']}]" if p["link_flair_text"] else ""
        print(f"  {i:2d}. [{score:>5} pts, {comments:>3} comments, {age:>5.1f}h]{flair} {title}")
        if p["selftext"]:
            preview = p["selftext"][:120].replace("\n", " ")
            print(f"      {preview}...")

def main():
    load_env()

    parser = argparse.ArgumentParser(description="Reddit API — fetch subreddit posts")
    subparsers = parser.add_subparsers(dest="command")

    top_parser = subparsers.add_parser("top", help="Fetch top posts from subreddits")
    top_parser.add_argument("subreddits", nargs="+", help="Subreddit names (without r/)")
    top_parser.add_argument("--period", default="day", choices=["hour", "day", "week", "month", "year", "all"])
    top_parser.add_argument("--limit", type=int, default=10)
    top_parser.add_argument("--out", help="Output JSON file")

    hot_parser = subparsers.add_parser("hot", help="Fetch hot posts from subreddits")
    hot_parser.add_argument("subreddits", nargs="+", help="Subreddit names (without r/)")
    hot_parser.add_argument("--limit", type=int, default=10)
    hot_parser.add_argument("--out", help="Output JSON file")

    post_parser = subparsers.add_parser("post", help="Fetch a single post by URL (incl. /s/ short URLs) or post ID, with top comments")
    post_parser.add_argument("target", help="Full post URL, /s/ short URL, or bare post ID")
    post_parser.add_argument("--limit", type=int, default=10, help="Number of top comments to print")
    post_parser.add_argument("--out", help="Output raw JSON file")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    token = get_access_token()

    if args.command == "post":
        post_id = extract_post_id(args.target)
        raw = fetch_post(token, post_id, comment_limit=args.limit)
        print_post(raw, comment_limit=args.limit)
        if args.out:
            out_path = Path(args.out)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(raw, indent=2, ensure_ascii=False))
            print(f"\nSaved to {args.out}")
        return

    sort = args.command
    period = getattr(args, "period", "day")
    all_posts = {}
    total = 0

    for sub in args.subreddits:
        raw = fetch_subreddit(token, sub, sort=sort, period=period, limit=args.limit)
        if raw and "data" in raw:
            posts = [format_post(p) for p in raw["data"]["children"]]
            all_posts[sub] = posts
            total += len(posts)
            print_summary(posts, sub)
        else:
            all_posts[sub] = []
            print(f"\nr/{sub}: fetch failed or empty")

    print(f"\nTotal: {total} posts across {len(args.subreddits)} subreddit(s)")

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(all_posts, indent=2, ensure_ascii=False))
        print(f"Saved to {args.out}")

if __name__ == "__main__":
    main()
