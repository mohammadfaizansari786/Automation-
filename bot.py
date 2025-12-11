import tweepy
import feedparser
import os
import sys
import json
import datetime
import time
import random
import requests
import tempfile

# --- CONFIGURATION ---
# Free Tier Limit: 500 posts/month (~16/day).
DAILY_LIMIT = 16  
POSTS_PER_RUN = 1 

# --- STATIC FACTS (Fallback) ---
CAR_FACTS = [
    "🏎️ Did you know? A modern F1 car generates enough downforce to drive upside down at 120mph!",
    "🚗 Fact: The Toyota Corolla is the best-selling car nameplate in history (50M+ sold).",
    "🚙 Trivia: The first speeding ticket was issued in 1902 for going 45mph.",
    "🔧 Fact: The average car is made of ~30,000 unique parts.",
    "🛑 History: Volvo gave away the 3-point seatbelt patent in 1959 to save lives.",
    "⚡ Fact: The first electric car was built in 1832, decades before the first gas engine.",
    "🐎 Trivia: The Ford Mustang was almost named the 'Cougar' or 'Torino'.",
    "💨 Fact: Top Fuel dragsters accelerate faster than the Space Shuttle.",
    "🛣️ Did you know? 65% of the German Autobahn has no speed limit.",
    "🚗 Stat: 95% of a car's lifetime is spent parked.",
    "🏎️ History: The first Le Mans 24 Hours race was held in 1923.",
    "🚙 Trivia: Volkswagen Group owns Audi, Bentley, Bugatti, Lamborghini, Porsche, and Ducati.",
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
        "https://www.motorsport.com/rss/nascar/news/",
    ],
    "CARS_AND_LEAKS": [
        "https://www.carscoops.com/feed/",
        "https://www.motor1.com/rss/category/spy/",
        "https://www.autoblog.com/rss.xml",
        "https://www.caranddriver.com/rss/all.xml",
    ],
    "FACTS": ["INTERNAL_LIST"]
}

# KEYS
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("ACCESS_SECRET")

# FILES
HISTORY_FILE = "posted_ids.txt"
STATE_FILE = "bot_state.json"

# --- AUTHENTICATION ---
def get_clients():
    if not API_KEY or not API_SECRET:
        print("❌ Error: API Keys missing.")
        sys.exit(1)

    # v2 Client (For Posting Text)
    client_v2 = tweepy.Client(
        consumer_key=API_KEY,
        consumer_secret=API_SECRET,
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_SECRET
    )

    # v1.1 API (For Media Uploads - Required for Free Tier images)
    auth = tweepy.OAuth1UserHandler(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET)
    api_v1 = tweepy.API(auth)

    return client_v2, api_v1

# --- HELPER FUNCTIONS ---
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

def extract_image_url(entry):
    """Attempts to find an image URL in the RSS entry"""
    # 1. Try 'media_content' (Standard RSS media)
    if 'media_content' in entry:
        media = entry.media_content
        if isinstance(media, list) and len(media) > 0:
            return media[0]['url']
            
    # 2. Try 'links' (Enclosures)
    if 'links' in entry:
        for link in entry.links:
            if link.get('type', '').startswith('image/'):
                return link['href']
                
    # 3. Try parsing summary for <img> tag (Basic check)
    if 'summary' in entry:
        if 'src="' in entry.summary:
            try:
                start = entry.summary.find('src="') + 5
                end = entry.summary.find('"', start)
                return entry.summary[start:end]
            except: pass
            
    return None

def download_and_upload_image(api_v1, image_url):
    """Downloads image to temp file and uploads to Twitter v1.1 API"""
    if not image_url: return None
    
    try:
        # Download
        response = requests.get(image_url, stream=True)
        if response.status_code != 200: return None
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp:
            for chunk in response.iter_content(1024):
                temp.write(chunk)
            temp_path = temp.name
            
        # Upload to Twitter
        print("   📸 Uploading image...")
        media = api_v1.media_upload(filename=temp_path)
        
        # Clean up
        os.remove(temp_path)
        
        return media.media_id
    except Exception as e:
        print(f"   ⚠️ Image upload failed: {e}")
        return None

def get_engagement_template(title, category):
    """Returns a catchy intro based on the content"""
    if category == "FACTS": return ""
    
    # Racing Templates
    if category == "RACING":
        templates = ["🏁 RACE UPDATE:", "🏎️ JUST IN:", "🚨 BREAKING:", "🗣️ PADDOCK TALK:"]
        if "Qualifying" in title: return "⏱️ QUALI REPORT:"
        if "Result" in title or "Winner" in title: return "🏆 RACE RESULT:"
        return random.choice(templates)
        
    # Car/Leak Templates
    if category == "CARS_AND_LEAKS":
        if "Spy" in title or "Leaked" in title:
            return random.choice(["📸 SPY SHOTS:", "👀 LEAKED:", "🕵️ SCOOP:"])
        return random.choice(["🚗 NEW REVEAL:", "⚡ AUTO NEWS:", "🚙 FIRST LOOK:"])
        
    return "🚨 NEWS:"

def get_smart_hashtags(url, title, category):
    tags = []
    url = url.lower()
    title = title.lower()

    if category == "FACTS": return "#CarFacts #DidYouKnow #Trivia #Motorsport"

    # Specific Topics
    if "f1" in url: tags.extend(["#F1", "#Formula1"])
    elif "wec" in url: tags.extend(["#WEC", "#LeMans", "#Hypercar"])
    elif "wrc" in url: tags.extend(["#WRC", "#Rally"])
    elif "motogp" in url: tags.extend(["#MotoGP"])
    elif "nascar" in url: tags.extend(["#NASCAR"])
    
    # Brands
    brands = ["ferrari", "porsche", "bmw", "mercedes", "ford", "toyota", "tesla", "audi", "lamborghini", "red bull"]
    for brand in brands:
        if brand in title: tags.append(f"#{brand.replace(' ', '')}")

    # Engagement Boosters
    boosters = ["#Motorsport", "#AutoNews", "#CarCulture", "#Racing"]
    tags.append(random.choice(boosters))
    
    return " ".join(list(dict.fromkeys(tags))[:4])

# --- MAIN BOT ---
def run():
    print("--- 🚀 High-Engagement Bot Starting ---")
    
    state = get_daily_state()
    print(f"📊 Daily Progress: {state['count']}/{DAILY_LIMIT}")
    
    if state["count"] >= DAILY_LIMIT:
        print("⛔ Daily limit reached.")
        return

    client_v2, api_v1 = get_clients()
    history = load_history()
    posts_made = 0
    
    # 1. Decide Category (Weighted: 45% Racing, 45% Cars, 10% Facts)
    choice = random.choices(["RACING", "CARS_AND_LEAKS", "FACTS"], weights=[45, 45, 10], k=1)[0]
    print(f"🎲 Category: {choice}")

    # 2. Handle FACTS
    if choice == "FACTS":
        fact = random.choice(CAR_FACTS)
        fact_id = f"fact_{hash(fact)}"
        
        if fact_id not in history:
            text = f"💡 {fact}\n\n#CarFacts #DidYouKnow #Trivia"
            try:
                print(f"   ➤ Posting Fact...")
                client_v2.create_tweet(text=text)
                save_history(fact_id)
                update_state(state["count"] + 1)
                posts_made = 1
            except Exception as e:
                print(f"   ❌ Error: {e}")

    # 3. Handle RSS with Media
    else:
        feeds = RSS_FEEDS[choice]
        random.shuffle(feeds)
        
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
                        
                        # 1. Get Image
                        image_url = extract_image_url(entry)
                        media_id = None
                        if image_url:
                            media_id = download_and_upload_image(api_v1, image_url)
                        
                        # 2. Build Text
                        intro = get_engagement_template(title, choice)
                        hashtags = get_smart_hashtags(feed_url, title, choice)
                        
                        # Max length calc (Link=23, Media doesn't count against text in v2 usually, but safe buffer)
                        reserved = len(link) + len(hashtags) + len(intro) + 15
                        max_len = 280 - reserved
                        if len(title) > max_len: title = title[:max_len-3] + "..."
                        
                        text = f"{intro} {title}\n\n🔗 {link}\n\n{hashtags}"
                        
                        try:
                            print(f"   ➤ Posting: {title[:30]}...")
                            
                            # Post with or without media
                            if media_id:
                                client_v2.create_tweet(text=text, media_ids=[media_id])
                            else:
                                client_v2.create_tweet(text=text)
                                
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
        print("💤 No suitable content found.")

if __name__ == "__main__":
    run()
