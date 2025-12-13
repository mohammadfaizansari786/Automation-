import tweepy
import os
import sys
import json
import datetime
import time
import random
import requests
import google.generativeai as genai
import tempfile

# --- CONFIGURATION ---
DAILY_LIMIT = 18

# --- TOPICS (Cars Only) ---
TOPICS = [
    "McLaren F1", "Ferrari F40", "Porsche 959", "Bugatti Chiron", "Pagani Huayra",
    "Lexus LFA", "Ford GT40", "Ferrari Enzo", "Nissan Skyline GT-R R34", "Mazda 787B",
    "Lamborghini Countach", "Mercedes 300SL Gullwing", "Aston Martin Valkyrie", 
    "Koenigsegg Jesko", "BMW E38", "Lancia Stratos", "Audi Quattro S1",
    "Porsche Carrera GT", "Jaguar E-Type", "Lamborghini Miura", "Dodge Viper ACR",
    "Subaru Impreza 22B", "Toyota Supra MK4", "Honda NSX-R", "Shelby Cobra 427"
]

# --- AUTHENTICATION ---
api_key = os.getenv("API_KEY")
api_secret = os.getenv("API_SECRET")
access_token = os.getenv("ACCESS_TOKEN")
access_secret = os.getenv("ACCESS_SECRET")

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_SEARCH_API_KEY = os.getenv("GOOGLE_SEARCH_API_KEY")
SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID")

HISTORY_FILE = "posted_ids.txt"
STATE_FILE = "bot_state.json"

def get_clients():
    if not api_key or not GEMINI_KEY:
        print("❌ Error: Missing API Keys.")
        sys.exit(1)

    client_v2 = tweepy.Client(consumer_key=api_key, consumer_secret=api_secret, access_token=access_token, access_token_secret=access_secret)
    auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
    api_v1 = tweepy.API(auth)
    
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
def generate_content(car_name):
    """
    Generates a 3-tweet thread about a specific car.
    """
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = (
        f"Write a 3-tweet thread admiring the legendary car '{car_name}'. "
        "Tweet 1: Focus on its iconic design and visual appeal. "
        "Tweet 2: Highlight its engine specs, horsepower, or unique engineering features. "
        "Tweet 3: Explain its legacy or why it is a collector's dream today. "
        "Separate each tweet strictly with '|||'. "
        "Keep each tweet under 240 chars. Use 2 hashtags total in the thread."
    )

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        parts = [p.strip() for p in text.split('|||') if p.strip()]
        return parts
    except Exception as e:
        print(f"   ⚠️ Gemini Error: {e}")
        return []

# --- 📸 IMAGES (ROBUST GOOGLE SEARCH) ---
def get_google_image(car_name):
    if not GOOGLE_SEARCH_API_KEY or not SEARCH_ENGINE_ID:
        print("❌ Missing Google Search Keys.")
        return None, None
    
    query = f"{car_name} car wallpaper 4k"
    print(f"   📸 Searching Google Images for: {query}")

    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        'q': query,
        'cx': SEARCH_ENGINE_ID,
        'key': GOOGLE_SEARCH_API_KEY,
        'searchType': 'image',
        'num': 3,  # Fetch 3 results in case the first fails
        'fileType': 'jpg',
        'safe': 'active'
    }

    # Headers to mimic a real browser (Prevents 403 Forbidden errors)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        resp = requests.get(url, params=params).json()
        items = resp.get('items', [])
        
        if not items:
            print("   ⚠️ No images found.")
            return None, None

        # Try downloading images one by one until successful
        for item in items:
            image_url = item['link']
            source_display = item.get('displayLink', 'Web Source')
            print(f"   ⬇️ Attempting download: {image_url}")

            try:
                img_resp = requests.get(image_url, headers=headers, timeout=10)
                
                # Check if download was actually successful
                if img_resp.status_code == 200 and len(img_resp.content) > 1000:
                    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                        f.write(img_resp.content)
                        print(f"   ✅ Image downloaded successfully ({len(img_resp.content)} bytes).")
                        return f.name, source_display
                else:
                    print(f"   ⚠️ Download failed (Status: {img_resp.status_code}). Trying next...")

            except Exception as e:
                print(f"   ⚠️ Error downloading specific image: {e}")
                continue

    except Exception as e:
        print(f"   ⚠️ Google Search API Error: {e}")
    
    print("   ❌ Could not download any valid image.")
    return None, None

# --- 🚀 POSTING LOGIC (THREADS) ---
def post_thread(client_v2, api_v1, tweets, image_path=None, image_credit=None):
    """
    Posts a thread. Attaches image to the first tweet if available.
    """
    first_tweet_id = None
    previous_tweet_id = None
    
    for i, text in enumerate(tweets):
        try:
            # Attach image to first tweet only
            media_ids = []
            if i == 0 and image_path:
                print(f"   📤 Uploading media: {image_path}")
                try:
                    media = api_v1.media_upload(filename=image_path)
                    media_ids = [media.media_id]
                    print("   ✅ Media upload successful.")
                except Exception as e:
                    print(f"   ❌ Media upload failed: {e}")
                    media_ids = [] # Continue without image if upload fails

            # Post Tweet
            if i == 0:
                if media_ids:
                    resp = client_v2.create_tweet(text=text, media_ids=media_ids)
                else:
                    resp = client_v2.create_tweet(text=text)
                first_tweet_id = resp.data['id']
                previous_tweet_id = first_tweet_id
            else:
                # Reply to previous
                resp = client_v2.create_tweet(text=text, in_reply_to_tweet_id=previous_tweet_id)
                previous_tweet_id = resp.data['id']
                
            time.sleep(2) # Safety delay
            
        except Exception as e:
            print(f"   ❌ Error posting tweet {i+1}: {e}")
            return False

    return True

# --- 🏁 RUNNERS ---

def run_car_post(client_v2, api_v1, history):
    topic = random.choice([t for t in TOPICS if t not in history] or TOPICS)
    print(f"   🏎️ Selected Car: {topic}")
    
    # 1. Get Image
    img_path, credit = get_google_image(topic)
    
    # 2. Get Thread Content
    tweet_parts = generate_content(topic)
    if not tweet_parts: return False
    
    # 3. Post
    success = post_thread(client_v2, api_v1, tweet_parts, img_path, credit)
    
    # Cleanup
    if img_path and os.path.exists(img_path):
        os.remove(img_path)
        
    if success:
        save_history(topic)
        print("   ✅ Car Thread Posted.")
    return success

def run():
    print("--- 🤖 CAR BOT INITIATED ---")
    
    state = get_daily_state()
    if state["count"] >= DAILY_LIMIT:
        print("⛔ Daily limit reached.")
        return

    client_v2, api_v1 = get_clients()
    history = load_history()
    
    success = run_car_post(client_v2, api_v1, history)
        
    if success:
        update_state(state["count"] + 1)

if __name__ == "__main__":
    run()
