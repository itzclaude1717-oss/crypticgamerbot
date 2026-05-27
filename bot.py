import tweepy
import openai
import requests
import schedule
import time
import os
import random
import feedparser
from datetime import datetime

# === CREDENTIALS FROM ENVIRONMENT ===
TWITTER_API_KEY             = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET          = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN        = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
TWITTER_BEARER_TOKEN        = os.getenv("TWITTER_BEARER_TOKEN")
OPENAI_API_KEY              = os.getenv("OPENAI_API_KEY")

# === SETUP CLIENTS ===
openai.api_key = OPENAI_API_KEY

client = tweepy.Client(
    bearer_token=TWITTER_BEARER_TOKEN,
    consumer_key=TWITTER_API_KEY,
    consumer_secret=TWITTER_API_SECRET,
    access_token=TWITTER_ACCESS_TOKEN,
    access_token_secret=TWITTER_ACCESS_TOKEN_SECRET,
    wait_on_rate_limit=True
)

auth_v1 = tweepy.OAuth1UserHandler(
    TWITTER_API_KEY, TWITTER_API_SECRET,
    TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET
)
api_v1 = tweepy.API(auth_v1)

# === BRAND IDENTITY ===
BOT_NAME     = "CrypticGamer"
BOT_BIO      = (
    "Your daily dose of gaming news, hot takes, tips & drops. "
    "PC | Console | Mobile | Esports. No fluff — just gaming. 🎮 #Gaming #Esports"
)
BOT_LOCATION = "The Gaming Realm 🎮"

# === GAMING RSS FEEDS ===
RSS_FEEDS = [
    "https://www.ign.com/articles.rss",
    "https://www.gamespot.com/feeds/mashup/",
    "https://kotaku.com/rss",
    "https://www.pcgamer.com/rss/",
    "https://www.eurogamer.net/?format=rss",
    "https://www.polygon.com/rss/index.xml",
    "https://feeds.feedburner.com/RockPaperShotgun",
]

GAMING_KEYWORDS = [
    "game", "gaming", "gamer", "esports", "playstation", "xbox", "nintendo",
    "pc gaming", "steam", "epic games", "twitch", "streamer", "fps", "rpg",
    "open world", "dlc", "patch", "update", "review", "release", "trailer",
    "gameplay", "graphics", "mod", "indie", "AAA", "battle royale", "mmorpg",
    "console", "gpu", "game pass", "ps5", "series x", "switch", "valorant",
    "fortnite", "minecraft", "call of duty", "elden ring", "cyberpunk",
    "league of legends", "overwatch", "apex legends", "gta", "zelda",
]

# === TOP GAMING ACCOUNTS TO ENGAGE ===
TARGET_GAMING_ACCOUNTS = [
    "IGN",
    "GameSpot",
    "Kotaku",
    "PCGamer",
    "Polygon",
    "NintendoAmerica",
    "Xbox",
    "PlayStation",
    "EASPORTS",
    "RiotGames",
    "EpicGames",
    "Steam",
    "Twitch",
    "shroud",
    "Ninja",
    "TimTheTatman",
    "DrLupo",
    "xQc",
    "pokimane",
    "HasanAbi",
]

# === STATE TRACKING ===
last_mention_id   = None
followed_users    = set()
engaged_tweet_ids = set()
liked_tweet_ids   = set()
MY_USER_ID        = None


# ================================================================
#  UTILITIES
# ================================================================

def get_my_user_id():
    try:
        me = client.get_me()
        return me.data.id
    except Exception as e:
        print(f"Error getting user ID: {e}")
        return None


def get_gaming_news():
    articles = []
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:
                title   = entry.get("title", "").lower()
                summary = entry.get("summary", "").lower()
                if any(kw in title or kw in summary for kw in GAMING_KEYWORDS):
                    articles.append({
                        "title":   entry.get("title", ""),
                        "link":    entry.get("link", ""),
                        "summary": entry.get("summary", "")[:200]
                    })
        except Exception as e:
            print(f"RSS error ({feed_url}): {e}")
    random.shuffle(articles)
    return articles[:6] if articles else []


def ask_gpt(prompt, max_tokens=280):
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are CrypticGamer — a sharp, opinionated gaming personality on Twitter/X. "
                        "You cover: PC gaming, PlayStation, Xbox, Nintendo, mobile, esports, "
                        "game releases, patches, hot takes, tips, and gaming culture. "
                        "Your goal is to grow a massive gaming following by being entertaining, "
                        "relatable, and dropping real knowledge gamers actually care about. "
                        "Tweet style: punchy, hype, gamer slang — under 260 characters. "
                        "Emojis: 🎮🔥💥👾🕹️ — tasteful. "
                        "Hashtags: max 2-3 from #Gaming #Gamer #Esports #PS5 #Xbox #Nintendo "
                        "#PCGaming #GamersUnite #NewGame #GamingCommunity. "
                        "Be bold. Make real hot takes. Never say 'As an AI'."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.88
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"GPT error: {e}")
        return None


def post_tweet(text, reply_to_id=None):
    try:
        if not text or len(text) > 280:
            print(f"Tweet skipped — {len(text) if text else 0} chars")
            return None
        if reply_to_id:
            result = client.create_tweet(text=text, in_reply_to_tweet_id=reply_to_id)
        else:
            result = client.create_tweet(text=text)
        print(f"[{datetime.now().strftime('%H:%M')}] POSTED: {text[:80]}...")
        return result
    except Exception as e:
        print(f"Tweet error: {e}")
        return None


# ================================================================
#  BRANDING
# ================================================================

def setup_gaming_profile():
    print("Setting up gaming brand profile...")
    try:
        api_v1.update_profile(
            name=BOT_NAME,
            description=BOT_BIO,
            location=BOT_LOCATION
        )
        print(f"Profile updated: '{BOT_NAME}' | bio set | location: {BOT_LOCATION}")
    except Exception as e:
        print(f"Profile setup error: {e}")


# ================================================================
#  CONTENT
# ================================================================

def post_gaming_news_tweet():
    articles = get_gaming_news()
    if articles:
        article = random.choice(articles)
        prompt = (
            f"Write a punchy gaming tweet reacting to this news: '{article['title']}'. "
            f"Summary: {article['summary']}. "
            "Hot take or hype reaction. Under 240 chars. Include relevant hashtags."
        )
    else:
        topics = [
            "a hot take about the current state of AAA gaming",
            "a tip for getting better at FPS games",
            "which console is winning 2025 and why",
            "a controversial gaming opinion that will spark debate",
            "the most underrated game of the past year",
            "why PC gaming is the superior platform",
            "what makes a perfect open world game",
            "the best gaming moment you can relate to",
            "the most hyped upcoming game release",
            "why game prices keep going up but quality doesn't",
        ]
        prompt = f"Write a gaming tweet about: {random.choice(topics)}. Under 240 chars. Include hashtags."
    tweet = ask_gpt(prompt)
    if tweet:
        post_tweet(tweet)


def post_esports_update():
    prompt = random.choice([
        "Give a hot esports take — recent tournament results, team rankings, or pro player drama. Under 240 chars.",
        "Write a tweet hyping up competitive gaming — esports, tournaments, or pro teams. Under 240 chars.",
        "Tweet about which esports title has the best competitive scene right now and why. Under 240 chars.",
    ])
    tweet = ask_gpt(prompt)
    if tweet:
        post_tweet(tweet)


def post_gaming_tip():
    games = [
        "Valorant", "Fortnite", "Minecraft", "Elden Ring", "Call of Duty",
        "Apex Legends", "League of Legends", "Overwatch 2", "GTA Online",
        "FIFA/EA Sports FC", "Rocket League", "Cyberpunk 2077", "Hogwarts Legacy"
    ]
    game = random.choice(games)
    prompt = (
        f"Write a useful gaming tip or trick for {game} that most players don't know. "
        "Keep it under 240 chars. Make it feel like insider knowledge."
    )
    tweet = ask_gpt(prompt)
    if tweet:
        post_tweet(tweet)


def post_gaming_poll_or_debate():
    debates = [
        "Xbox vs PlayStation — settle it once and for all",
        "PC vs console gaming — which is actually better",
        "Games are too expensive now — agree or disagree",
        "The best gaming era: 2000s, 2010s, or 2020s",
        "Is single-player gaming dying?",
        "Are remakes ruining gaming?",
        "Cross-platform play — should every game have it?",
    ]
    prompt = (
        f"Write a tweet starting a debate or asking the gaming community about: "
        f"'{random.choice(debates)}'. Make it engaging, under 240 chars."
    )
    tweet = ask_gpt(prompt)
    if tweet:
        post_tweet(tweet)


# ================================================================
#  ENGAGEMENT
# ================================================================

def engage_top_gaming_tweets():
    try:
        keywords = random.sample(GAMING_KEYWORDS[:20], 3)
        query = " OR ".join(keywords) + " -is:retweet lang:en"
        tweets = client.search_recent_tweets(
            query=query, max_results=10, tweet_fields=["author_id", "public_metrics"]
        )
        if not tweets.data:
            return
        top_tweets = sorted(
            tweets.data, key=lambda t: t.public_metrics.get("like_count", 0), reverse=True
        )[:3]
        for tweet in top_tweets:
            if tweet.id in engaged_tweet_ids:
                continue
            prompt = (
                f"Write a short, genuine gaming reply to this tweet: '{tweet.text}'. "
                "Be a fellow gamer — 1-2 sentences, no hashtags, under 200 chars."
            )
            reply = ask_gpt(prompt, max_tokens=150)
            if reply:
                post_tweet(reply, reply_to_id=tweet.id)
                engaged_tweet_ids.add(tweet.id)
            time.sleep(5)
    except Exception as e:
        print(f"Engage top tweets error: {e}")


def engage_gaming_accounts():
    global MY_USER_ID
    if not MY_USER_ID:
        return
    account = random.choice(TARGET_GAMING_ACCOUNTS)
    try:
        user = client.get_user(username=account)
        if not user.data:
            return
        tweets = client.get_users_tweets(id=user.data.id, max_results=5, tweet_fields=["public_metrics"])
        if not tweets.data:
            return
        tweet = tweets.data[0]
        if tweet.id in engaged_tweet_ids:
            return
        prompt = (
            f"Write a short gamer reply to @{account}'s tweet: '{tweet.text}'. "
            "Sound like a real gamer fan. Under 180 chars. No hashtags."
        )
        reply = ask_gpt(prompt, max_tokens=120)
        if reply:
            post_tweet(reply, reply_to_id=tweet.id)
            engaged_tweet_ids.add(tweet.id)
    except Exception as e:
        print(f"Engage {account} error: {e}")


def like_gaming_content():
    try:
        global MY_USER_ID
        if not MY_USER_ID:
            return
        game = random.choice(GAMING_KEYWORDS[:15])
        tweets = client.search_recent_tweets(query=f"{game} -is:retweet lang:en", max_results=10)
        if not tweets.data:
            return
        for tweet in tweets.data[:3]:
            if tweet.id not in liked_tweet_ids:
                client.like(MY_USER_ID, tweet.id)
                liked_tweet_ids.add(tweet.id)
                time.sleep(3)
    except Exception as e:
        print(f"Like error: {e}")


def reply_to_mentions():
    global last_mention_id, MY_USER_ID
    if not MY_USER_ID:
        return
    try:
        kwargs = {"max_results": 5}
        if last_mention_id:
            kwargs["since_id"] = last_mention_id
        mentions = client.get_users_mentions(MY_USER_ID, **kwargs)
        if not mentions.data:
            return
        last_mention_id = mentions.data[0].id
        for mention in mentions.data:
            prompt = (
                f"Reply to this tweet mentioning you as CrypticGamer: '{mention.text}'. "
                "Be fun, short, gamer-friendly. Under 200 chars."
            )
            reply = ask_gpt(prompt, max_tokens=120)
            if reply:
                post_tweet(reply, reply_to_id=mention.id)
            time.sleep(5)
    except Exception as e:
        print(f"Mention reply error: {e}")


def follow_back_gamers():
    global MY_USER_ID
    if not MY_USER_ID:
        return
    try:
        followers = client.get_users_followers(MY_USER_ID, max_results=20)
        if not followers.data:
            return
        for user in followers.data:
            if user.id not in followed_users:
                client.follow_user(MY_USER_ID, user.id)
                followed_users.add(user.id)
                print(f"Followed back: @{user.username}")
                time.sleep(3)
    except Exception as e:
        print(f"Follow-back error: {e}")


def strategic_follow_gamers():
    account = random.choice(TARGET_GAMING_ACCOUNTS)
    try:
        user = client.get_user(username=account)
        if not user.data:
            return
        followers = client.get_users_followers(user.data.id, max_results=10)
        if not followers.data:
            return
        global MY_USER_ID
        if not MY_USER_ID:
            return
        count = 0
        for follower in followers.data:
            if follower.id not in followed_users and count < 3:
                client.follow_user(MY_USER_ID, follower.id)
                followed_users.add(follower.id)
                count += 1
                time.sleep(3)
        print(f"Strategic follow: {count} gamers from @{account}'s followers")
    except Exception as e:
        print(f"Strategic follow error: {e}")


# ================================================================
#  MAIN SCHEDULER
# ================================================================

def run_scheduler():
    global MY_USER_ID

    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M')}] CrypticGamer Bot starting...\n" + "="*60)

    MY_USER_ID = get_my_user_id()
    if not MY_USER_ID:
        print("WARNING: Could not get user ID — engagement features disabled.")

    setup_gaming_profile()

    intro = ask_gpt(
        "Write an intro tweet for CrypticGamer, a new gaming Twitter account. "
        "Bold, hype, makes gamers want to follow immediately. Under 270 chars. #Gaming #Gamer"
    )
    if intro:
        post_tweet(intro)

    schedule.every().day.at("07:00").do(post_gaming_news_tweet)
    schedule.every().day.at("09:00").do(post_gaming_tip)
    schedule.every().day.at("11:00").do(post_gaming_poll_or_debate)
    schedule.every().day.at("13:00").do(post_gaming_news_tweet)
    schedule.every().day.at("15:00").do(post_esports_update)
    schedule.every().day.at("17:00").do(post_gaming_tip)
    schedule.every().day.at("20:00").do(post_gaming_news_tweet)
    schedule.every().day.at("22:00").do(post_gaming_poll_or_debate)

    schedule.every(45).minutes.do(engage_top_gaming_tweets)
    schedule.every(2).hours.do(engage_gaming_accounts)
    schedule.every(1).hours.do(like_gaming_content)
    schedule.every(30).minutes.do(reply_to_mentions)
    schedule.every(1).hours.do(follow_back_gamers)
    schedule.every(3).hours.do(strategic_follow_gamers)

    print("\nSchedule active:")
    print(f"  Content:              7am 9am 11am 1pm 3pm 5pm 8pm 10pm")
    print(f"  Engage top tweets:    every 45 min")
    print(f"  Engage influencers:   every 2 hrs")
    print(f"  Like gaming content:  every 1 hr")
    print(f"  Reply to mentions:    every 30 min")
    print(f"  Follow-back:          every 1 hr")
    print(f"  Strategic follows:    every 3 hrs")
    print("="*60 + "\n")

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    run_scheduler()
