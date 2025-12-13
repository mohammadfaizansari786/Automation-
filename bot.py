import tweepy
import os
import sys
import json
import datetime
import time
import random
import requests
import google.generativeai as genai

# --- CONFIGURATION ---
DAILY_LIMIT = 18

# --- TOPICS (Fallback if no news) ---
TOPICS = {
    "CARS": [
        "McLaren F1", "Ferrari F40", "Porsche 959", "Bugatti Chiron", "Pagani Huayra",
        "Lexus LFA", "Ford GT", "Ferrari Enzo", "Nissan GT-R R34", "Mazda 787B",
        "Lamborghini Countach", "Mercedes 300SL", "Aston Martin Valkyrie", "Koenigsegg Jesko"
    ],
    "TECH": [
        "W16 Engine", "V12 Engine", "Turbocharger", "Dual-clutch transmission", 
        "Active Aerodynamics", "KERS System", "Carbon-Ceramic Brakes", "Pushrod Suspension"
    ]
}

# --- AUTHENTICATION & SETUP ---
# 1. Twitter
api_key = os.getenv("API_KEY")
api_secret = os.getenv("API_SECRET")
access_token = os.getenv("ACCESS_TOKEN")
access_secret = os.getenv("ACCESS_SECRET")

# 2. New APIs
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
UNSPLASH_KEY = os.getenv("UNSPLASH_ACCESS_KEY")
NEWS_KEY = os.getenv("NEWS_API_KEY")

# Files
HISTORY_FILE = "posted_ids.txt"
STATE_FILE = "bot_state.json"

def get_clients():
    if not api_key or not GEMINI_KEY:
        print("❌ Error: Missing API Keys (Twitter or Gemini).")
        sys.exit(1)

    # Twitter
    client_v2 = tweepy.Client(consumer_key=api_key, consumer_secret=api_secret, access_token=access_token, access_token_secret=access_secret)
    auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
    api_v1 = tweepy.API(auth)
    
    # Gemini
    genai.configure(api_key=GEMINI_KEY)
    
    return client_v2, api_v1

# --- HELPER FUNCTIONS ---
def load_history():
    if not os.path.exists(HISTORY_FILE): return set()
    with open(HISTORY_FILE, "r") as f: return set(line.strip() for line in f if line.strip())

def save_history(entry_id):
    with open(HISTORY_FILE, "a") as f: f.write(f"{entry_id}\n")

def get_daily_state():
    today = datetime.date.today().isoformat()
    default = {"date": today, "count": 0}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
                if state.get("date") != today: return default
                return state
        except: return default
    return default

def update_state(count):
    today = datetime.date.today().isoformat()
    with open(STATE_FILE, "w") as f: json.dump({"date": today, "count": count}, f)

# --- 🧠 AI BRAIN (GEMINI) ---
def generate_tweet_content(prompt_type, topic_data):
    """Uses Google Gemini to write the tweet text."""
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    if prompt_type == "NEWS":
        prompt = (
            f"Write a professional, engaging Twitter post (under 240 chars) about this car news: '{topic_data}'. "
            "Include 2 relevant hashtags. Do not use quotes."
        )
    elif prompt_type == "TECH":
        prompt = (
            f"Write a professional, educational Twitter thread hook (under 240 chars) about automotive tech: '{topic_data}'. "
            "Make it sound like an engineering expert. Include 2 hashtags."
        )
    else: # CARS
        prompt = (
            f"Write a professional, admiring Twitter thread hook (under 240 chars) about the car '{topic_data}'. "
            "Focus on its legacy or engineering. Include 2 hashtags."
        )

    try:
        response = model.generate_content(prompt)
        return response.text.strip().replace('"', '')
    except Exception as e:
        print(f"   ⚠️ Gemini Error: {e}")
        return None

# --- 📸 IMAGES (UNSPLASH) ---
def get_unsplash_image(query):
    if not UNSPLASH_KEY: return None
    print(f"   📸 Searching Unsplash for: {query}")
    try:
        url = f"https://api.unsplash.com/search/photos?query={query}&per_page=1&orientation=landscape&client_id={UNSPLASH_KEY}"
        resp = requests.get(url).json()
        if resp['results']:
            image_url = resp['results'][0]['urls']['regular']
            # Download it
            img_data = requests.get(image_url).content
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                f.write(img_data)
                return f.name, resp['results'][0]['user']['name'] # Return path and credit
    except Exception as e:
        print(f"   ⚠️ Unsplash Error: {e}")
    return None, None

# --- 📰 NEWS (NEWSAPI) ---
def get_latest_news(history):
    if not NEWS_KEY: return None
    print("   📰 Checking NewsAPI...")
    # Search for general automotive news
    url = f"https://newsapi.org/v2/everything?q=supercar OR 'F1 racing' OR 'automotive engineering'&sortBy=publishedAt&language=en&apiKey={NEWS_KEY}"
    try:
        data = requests.get(url).json()
        for article in data.get('articles', [])[:5]:
            # Use URL as ID
            if article['url'] in history: continue
            
            return {
                "title": article['title'],
                "url": article['url'],
                "desc": article['description']
            }
    except Exception as e:
        print(f"   ⚠️ NewsAPI Error: {e}")
    return None

# --- 🏁 RUNNERS ---

def run_news_post(client_v2, history):
    news = get_latest_news(history)
    if not news: return False

    print(f"   Found News: {news['title']}")
    
    # AI writes the tweet
    tweet_text = generate_tweet_content("NEWS", news['title'])
    if not tweet_text: tweet_text = f"🚨 NEWS: {news['title']}"

    # Append Link
    final_text = f"{tweet_text}\n\n🔗 {news['url']}"
    
    try:
        client_v2.create_tweet(text=final_text)
        save_history(news['url'])
        print("   ✅ News Posted.")
        return True
    except Exception as e:
        print(f"   ❌ News Post Failed: {e}")
        return False

def run_encyclopedia_post(client_v2, api_v1, history):
    # Pick Topic
    cat = random.choice(["CARS", "TECH"])
    topic = random.choice([t for t in TOPICS[cat] if t not in history] or TOPICS[cat])
    
    print(f"   📚 Topic: {topic}")
    
    # 1. Get Image
    img_path, photographer = get_unsplash_image(topic + " car")
    
    # 2. Get AI Text
    tweet_text = generate_tweet_content(cat, topic)
    if not tweet_text: return False
    
    # Add image credit if using Unsplash
    if photographer:
        tweet_text += f"\n\n(📸: {photographer} on Unsplash)"

    try:
        if img_path:
            media = api_v1.media_upload(filename=img_path)
            client_v2.create_tweet(text=tweet_text, media_ids=[media.media_id])
            os.remove(img_path)
        else:
            client_v2.create_tweet(text=tweet_text)
            
        save_history(topic)
        print("   ✅ Encyclopedia Post Posted.")
        return True
    except Exception as e:
        print(f"   ❌ Encyclopedia Post Failed: {e}")
        return False

def run():
    print("--- 🤖 SUPER-BOT INITIATED ---")
    
    state = get_daily_state()
    if state["count"] >= DAILY_LIMIT:
        print("⛔ Daily limit reached.")
        return

    client_v2, api_v1 = get_clients()
    history = load_history()
    
    # 40% Chance News, 60% Chance Encyclopedia
    if random.random() < 0.4:
        success = run_news_post(client_v2, history)
        if not success: # Fallback
            success = run_encyclopedia_post(client_v2, api_v1, history)
    else:
        success = run_encyclopedia_post(client_v2, api_v1, history)
        
    if success:
        update_state(state["count"] + 1)

if __name__ == "__main__":
    run()
    
