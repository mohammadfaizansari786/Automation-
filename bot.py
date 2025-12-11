import tweepy
import feedparser
import os
import sys
import json
import datetime
import time
import random

# --- CONFIGURATION ---
# Free Tier Limit: 500 posts/month.
# 16 posts/day * 31 days = 496. Safe!
DAILY_LIMIT = 16  
POSTS_PER_RUN = 1  

# --- STATIC FACTS (Fallback Content) ---
# Used if we want to post a "Fact" but no RSS feed is handy
CAR_FACTS = [
    "🏎️ Did you know? A modern F1 car can drive upside down in a tunnel at 120mph due to aerodynamic downforce!",
    "🚗 Fact: The Toyota Corolla is the best-selling car nameplate in history, with over 50 million sold.",
    "🚙 Trivia: The first speeding ticket was issued in 1902 to a driver going 45mph.",
    "🔧 Fact: The average car has about 30,000 parts.",
    "🛑 Did you know? Volvo invented the 3-point seatbelt in 1959 and gave the patent away for free to save lives.",
    "⚡ Fact: The first electric car was built in 1832, long before the first gas engine.",
    "🐎 Trivia: The Ford Mustang was almost named the Ford Cougar.",
    "💨 Fact: Top Fuel dragsters accelerate faster than a space shuttle launch.",
    "🛣️ Did you know? The Autobahn has no speed limit on about 65% of its highways.",
    "🚗 Fact: 95% of a car's lifetime is spent parked.",
    "🏎️ History: The first Le Mans 24 Hours race was held in 1923.",
    "🚙 Trivia: Volkswagen owns Audi, Bentley, Bugatti, Lamborghini, Porsche, and Ducati.",
]

# --- RSS SOURCES ---
RSS_FEEDS = {
    "RACING": [
        "https://www.motorsport.com/rss/f1/news/",
        "https://www.racefans.net/feed/",
        "https://www.motorsport.com/rss/wec/news/",
        "https://www.motorsport.com/rss/wrc/news/",
        "https://dirtfish.com/feed/",
        "https://www.crash.net/rss/motogp",
    ],
    "CARS_AND_LEAKS": [
        "https://www.carscoops.com/feed/",             # Great for Spies/Scoops
        "https://www.motor1.com/rss/category/spy/",    # Dedicated Spy Shots
        "https://www.autoblog.com/rss.xml",            # General New Cars
        "https://www.caranddriver.com/rss/all.xml",    # Reviews/News
    ],
    "FACTS": [
        "INTERNAL_LIST" # Special marker to use the list above
    ]
}

# KEYS
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("ACCESS_SECRET")

# FILES
HISTORY_FILE = "posted_ids.txt"
STATE_FILE = "bot_state.json"

# --- HELPER FUNCTIONS ---
def get_client():
    if not API_KEY or not API_SECRET:
        print("❌ Error: API Keys missing.")
        sys.exit(1)
    return tweepy.Client(
        consumer_key=API_KEY,
        consumer_secret=API_SECRET,
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_SECRET
    )

def load_history():
    if not os.path.exists(HISTORY_FILE): return set()
    with open(HISTORY_FILE, "r") as f:
        return set(line.strip() for line in f if line.strip())

def save_history(post_id):
    with open(HISTORY_FILE, "a") as f:
        f.write(f"{post_id}\n")

def get_daily_state():
    today = datetime.date.today().isoformat()
    default_state = {"date": today, "count": 0}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
                if state.get("date") != today: return default_state
                return state
        except: return default_state
    return default_state

def update_state(count):
    today = datetime.date.today().isoformat()
    with open(STATE_FILE, "w") as f:
        json.dump({"date": today, "count": count}, f)

def get_smart_hashtags(url, title, category):
    tags = []
    url = url.lower()
    title = title.lower()

    if category == "FACTS":
        return "#CarFacts #DidYouKnow #Automotive #Trivia"

    # Leaks & Spies
    if "spy" in url or "scoop" in url or "leak" in title:
        tags.extend(["#SpyShot", "#CarLeak", "#FutureCars", "#Rumor"])
    # New Cars
    elif "reveal" in title or "2025" in title or "2026" in title:
        tags.extend(["#NewCar", "#CarReveal", "#Automotive"])
    # Racing
    elif "f1" in url: tags.append("#F1")
    elif "wec" in url: tags.append("#WEC")
    elif "wrc" in url: tags.append("#WRC")
    
    # Brand detection (Simple check)
    brands = ["ferrari", "porsche", "bmw", "mercedes", "ford", "toyota", "tesla", "audi", "lamborghini"]
    for brand in brands:
        if brand in title:
            tags.append(f"#{brand.capitalize()}")

    # Add engagement booster
    tags.append("#CarNews")
    
    return " ".join(list(dict.fromkeys(tags))[:4])

# --- MAIN BOT ---
def run():
    print("--- 🚗 Ultimate Auto Bot Starting ---")
    
    state = get_daily_state()
    print(f"📊 Daily Progress: {state['count']}/{DAILY_LIMIT}")
    
    if state["count"] >= DAILY_LIMIT:
        print("⛔ Daily limit reached.")
        return

    client = get_client()
    history = load_history()
    posts_made = 0
    
    # 1. Decide Category (Weighted Random)
    # 50% Racing, 40% Cars/Leaks, 10% Facts
    choice = random.choices(["RACING", "CARS_AND_LEAKS", "FACTS"], weights=[5, 4, 1], k=1)[0]
    print(f"🎲 Selected Category: {choice}")

    # 2. Handle FACTS
    if choice == "FACTS":
        fact = random.choice(CAR_FACTS)
        # Simple hash of fact to avoid repetition
        fact_id = f"fact_{hash(fact)}"
        
        if fact_id not in history:
            text = f"{fact}\n\n#CarFacts #DidYouKnow #Motorsport"
            try:
                print(f"   ➤ Posting Fact: {fact[:30]}...")
                client.create_tweet(text=text)
                save_history(fact_id)
                update_state(state["count"] + 1)
                posts_made = 1
            except Exception as e:
                print(f"   ❌ Error: {e}")
        else:
            print("   ⚠️ Fact already posted. Skipping.")

    # 3. Handle RSS (Racing or Cars)
    else:
        feeds = RSS_FEEDS[choice]
        random.shuffle(feeds) # Shuffle to vary sources
        
        for feed_url in feeds:
            if posts_made > 0: break
            
            try:
                print(f"🔍 Scanning: {feed_url}")
                feed = feedparser.parse(feed_url)
                if not feed.entries: continue
                
                for entry in feed.entries[:5]:
                    if posts_made > 0: break
                    
                    post_id = getattr(entry, 'id', entry.link)
                    if post_id not in history:
                        title = entry.title
                        link = entry.link
                        
                        hashtags = get_smart_hashtags(feed_url, title, choice)
                        
                        # Truncate
                        reserved = len(link) + len(hashtags) + 12
                        max_len = 280 - reserved
                        if len(title) > max_len: title = title[:max_len-3] + "..."
                        
                        text = f"🚨 {title}\n\n🔗 {link}\n\n{hashtags}"
                        
                        try:
                            print(f"   ➤ Posting: {title[:30]}...")
                            client.create_tweet(text=text)
                            save_history(post_id)
                            history.add(post_id)
                            update_state(state["count"] + 1)
                            posts_made = 1
                            print("   ✅ Success!")
                        except Exception as e:
                            print(f"   ❌ API Error: {e}")
                            
            except Exception as e:
                print(f"   ⚠️ Feed Error: {e}")

    if posts_made == 0:
        print("💤 No suitable content found this run.")

if __name__ == "__main__":
    run()
    
