import tweepy
import feedparser
import os
import sys
import json
import datetime

# --- CONFIGURATION ---
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("ACCESS_SECRET")
BEARER_TOKEN = os.getenv("BEARER_TOKEN")

# Limit configuration
MAX_POSTS_PER_DAY = 3
POSTS_PER_RUN = 1 # Post only 1 item per hour to spread them out

RSS_FEEDS = [
    "https://www.motorsport.com/rss/f1/news/",
    "https://www.ign.com/feeds/games/rss",
    "https://www.reddit.com/r/GamingLeaksAndRumours/top/.rss?t=day"
]

HISTORY_FILE = "posted_ids.txt"
STATE_FILE = "bot_state.json"

# --- AUTHENTICATION ---
def get_twitter_client():
    return tweepy.Client(
        bearer_token=BEARER_TOKEN,
        consumer_key=API_KEY,
        consumer_secret=API_SECRET,
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_SECRET
    )

# --- FILE MANAGEMENT ---
def get_posted_ids():
    if not os.path.exists(HISTORY_FILE):
        open(HISTORY_FILE, 'a').close()
        return []
    with open(HISTORY_FILE, "r") as f:
        return f.read().splitlines()

def save_posted_id(post_id):
    with open(HISTORY_FILE, "a") as f:
        f.write(f"{post_id}\n")

def get_daily_state():
    today = datetime.date.today().isoformat()
    default_state = {"date": today, "count": 0}
    
    if not os.path.exists(STATE_FILE):
        return default_state
    
    try:
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
            # If the date in the file is not today, reset the counter
            if state.get("date") != today:
                return default_state
            return state
    except:
        return default_state

def update_state(count):
    today = datetime.date.today().isoformat()
    state = {"date": today, "count": count}
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

# --- MAIN LOGIC ---
def run_bot():
    print("--- Starting Bot Run ---")
    
    # 1. Check Daily Limit
    state = get_daily_state()
    print(f"Daily Status: {state['count']}/{MAX_POSTS_PER_DAY} posts used today ({state['date']}).")
    
    if state['count'] >= MAX_POSTS_PER_DAY:
        print("Daily limit reached. Sleeping until tomorrow.")
        return

    # 2. Prepare Connection
    if not API_KEY:
        print("Error: API Keys not found.")
        sys.exit(1)

    client = get_twitter_client()
    posted_ids = get_posted_ids()
    posts_made_this_run = 0
    
    # 3. Check Feeds
    for feed_url in RSS_FEEDS:
        # Stop if we hit the limit for this specific run
        if posts_made_this_run >= POSTS_PER_RUN:
            break

        print(f"Checking: {feed_url}")
        try:
            feed = feedparser.parse(feed_url)
            if not feed.entries:
                continue
            
            # Look at top 5 entries to find one we haven't posted
            for entry in feed.entries[:5]:
                post_id = entry.id if 'id' in entry else entry.link
                
                if post_id not in posted_ids:
                    title = entry.title
                    link = entry.link
                    
                    tweet_text = f"🚨 NEWS: {title}\n\nRead more: {link}\n\n#Gaming #Motorsport"
                    if len(tweet_text) > 280:
                        tweet_text = f"🚨 NEWS: {title[:200]}...\n\n{link}"

                    try:
                        print(f"Attempting to post: {title}")
                        client.create_tweet(text=tweet_text)
                        
                        # Success: Update all files
                        save_posted_id(post_id)
                        state['count'] += 1
                        update_state(state['count'])
                        
                        posts_made_this_run += 1
                        print(f"✅ Success! Total today: {state['count']}")
                        
                        # Stop looking at feeds once we post our 1 item
                        break 
                        
                    except Exception as e:
                        print(f"❌ Error posting to X: {e}")
                        
        except Exception as e:
            print(f"Error processing feed {feed_url}: {e}")

if __name__ == "__main__":
    run_bot()
