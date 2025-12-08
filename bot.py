import tweepy
import feedparser
import os
import sys

# --- CONFIGURATION ---
# We use os.getenv to read secrets from GitHub Settings
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("ACCESS_SECRET")
BEARER_TOKEN = os.getenv("BEARER_TOKEN")

RSS_FEEDS = [
    "https://www.motorsport.com/rss/f1/news/",
    "https://www.ign.com/feeds/games/rss",
    "https://www.reddit.com/r/GamingLeaksAndRumours/top/.rss?t=day"
]

HISTORY_FILE = "posted_ids.txt"

def get_twitter_client():
    return tweepy.Client(
        bearer_token=BEARER_TOKEN,
        consumer_key=API_KEY,
        consumer_secret=API_SECRET,
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_SECRET
    )

def get_posted_ids():
    # If file doesn't exist, create it
    if not os.path.exists(HISTORY_FILE):
        open(HISTORY_FILE, 'a').close()
        return []
    with open(HISTORY_FILE, "r") as f:
        return f.read().splitlines()

def save_posted_id(post_id):
    with open(HISTORY_FILE, "a") as f:
        f.write(f"{post_id}\n")

def run_bot():
    print("--- Starting Bot Run ---")
    
    # Check if keys are loaded (Basic Debugging)
    if not API_KEY:
        print("Error: API Keys not found in environment variables.")
        sys.exit(1)

    client = get_twitter_client()
    posted_ids = get_posted_ids()
    new_posts_count = 0
    
    for feed_url in RSS_FEEDS:
        print(f"Checking: {feed_url}")
        try:
            feed = feedparser.parse(feed_url)
            if not feed.entries:
                continue
            
            # Look at the top 3 entries, not just the first one, 
            # in case multiple stories broke since the last run
            for entry in feed.entries[:3]:
                post_id = entry.id if 'id' in entry else entry.link
                
                if post_id not in posted_ids:
                    title = entry.title
                    link = entry.link
                    
                    tweet_text = f"🚨 NEWS: {title}\n\nRead more: {link}\n\n#Gaming #Motorsport"
                    if len(tweet_text) > 280:
                        tweet_text = f"🚨 NEWS: {title[:200]}...\n\n{link}"

                    try:
                        client.create_tweet(text=tweet_text)
                        print(f"Posted: {title}")
                        save_posted_id(post_id)
                        posted_ids.append(post_id) # Update local list so we don't double post in this loop
                        new_posts_count += 1
                    except Exception as e:
                        print(f"Error posting to X: {e}")
                        
        except Exception as e:
            print(f"Error processing feed {feed_url}: {e}")
            
    if new_posts_count == 0:
        print("No new updates found.")

if __name__ == "__main__":
    run_bot()
  
