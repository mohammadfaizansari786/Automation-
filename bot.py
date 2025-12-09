import tweepy
import feedparser
import os
import sys
import json
import datetime
import time

# --- CONFIGURATION ---
# 1. LIMITS
DAILY_LIMIT = 16  # 16 posts x 30 days = 480 posts/month (Safe buffer for 500 limit)

# 2. BETTER SOURCES (Mix of News & Leaks)
RSS_FEEDS = [
    # --- F1 & Cars ---
    "https://www.motorsport.com/rss/f1/news/", 
    "https://www.racefans.net/feed/",
    "https://www.autoblog.com/rss.xml",
    
    # --- Gaming (News + Leaks) ---
    "https://www.reddit.com/r/GamingLeaksAndRumours/top/.rss?t=day", # Best for leaks
    "https://www.gematsu.com/feed", # Best for Japanese game news
    "https://www.videogameschronicle.com/feed/", # Reliable scoops
    
    # --- Movies & Series ---
    "https://deadline.com/feed/", # Hollywood industry standard
    "https://www.reddit.com/r/MarvelStudiosSpoilers/new/.rss",
    "https://screenrant.com/feed/"
]

# 3. KEYS
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("ACCESS_SECRET")

# 4. FILES
HISTORY_FILE = "posted_ids.txt"
STATE_FILE = "bot_state.json"

# --- HELPER FUNCTIONS ---
def get_client():
    if not API_KEY:
        print("❌ Error: API Keys missing.")
        sys.exit(1)
    return tweepy.Client(
        consumer_key=API_KEY,
        consumer_secret=API_SECRET,
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_SECRET
    )

def load_history():
    if not os.path.exists(HISTORY_FILE): return []
    with open(HISTORY_FILE, "r") as f:
        return f.read().splitlines()

def save_history(post_id):
    with open(HISTORY_FILE, "a") as f:
        f.write(f"{post_id}\n")

def check_daily_limit():
    """Checks if we have hit the 16 posts/day limit"""
    today = datetime.date.today().isoformat()
    
    # Load state
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            try:
                state = json.load(f)
            except:
                state = {"date": today, "count": 0}
    else:
        state = {"date": today, "count": 0}

    # Reset counter if it's a new day
    if state["date"] != today:
        state = {"date": today, "count": 0}
        
    print(f"📊 Daily Stats: {state['count']}/{DAILY_LIMIT} posts used.")
    return state

def update_daily_limit(state):
    state["count"] += 1
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

# --- MAIN BOT ---
def run():
    print("--- 🤖 Smart Bot Starting ---")
    
    # 1. Check Limits
    state = check_daily_limit()
    if state["count"] >= DAILY_LIMIT:
        print("⛔ Daily limit reached. Stopping to save monthly quota.")
        return

    client = get_client()
    history = load_history()
    
    # 2. Find ONE new thing to post
    # We iterate through feeds until we find 1 good candidate
    post_made = False
    
    for feed_url in RSS_FEEDS:
        if post_made: break # Stop if we posted 1 thing
        
        try:
            print(f"🔍 Scanning: {feed_url}")
            feed = feedparser.parse(feed_url)
            if not feed.entries: continue
            
            # Look at top 5 recent entries
            for entry in feed.entries[:5]:
                post_id = entry.id if 'id' in entry else entry.link
                
                if post_id not in history:
                    title = entry.title
                    link = entry.link
                    
                    # Formatting: Clean and punchy
                    hashtags = "#News #Gaming #Motorsport"
                    if "reddit" in feed_url: hashtags += " #Leaks #Rumor"
                    
                    text = f"🚨 {title}\n\n🔗 {link}\n\n{hashtags}"
                    
                    # Truncate to 280
                    if len(text) > 280:
                        text = f"🚨 {title[:180]}...\n\n🔗 {link}\n\n{hashtags}"
                    
                    try:
                        print(f"   ➤ Posting: {title}")
                        client.create_tweet(text=text)
                        
                        save_history(post_id)
                        update_daily_limit(state)
                        post_made = True
                        print("   ✅ Success!")
                        break # Break inner loop
                        
                    except Exception as e:
                        print(f"   ❌ Error posting: {e}")
        except Exception as e:
            print(f"   ⚠️ Feed Error: {e}")

    if not post_made:
        print("💤 No new content found this run.")

if __name__ == "__main__":
    run()
