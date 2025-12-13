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
IMAGES_PER_TWEET = 4  # Twitter allows max 4 images per tweet

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
        print("❌ Error: Missing API Keys (Twitter or Gemini).")
        sys.exit(1)
    
    if not GOOGLE_SEARCH_API_KEY or not SEARCH_ENGINE_ID:
        print("❌ Error: Missing Google Search Keys.")
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

# --- 🧠 AI BRAIN (PROFESSIONAL WRITING STYLE) ---
def generate_content(car_name):
    """
    Generates a professional, journalist-style 3-tweet thread using Gemini.
    """
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = (
        f"Act as a distinguished automotive historian and professional journalist. "
        f"Write a refined, informative 3-tweet thread about the '{car_name}'.\n\n"
        
        "Tweet 1 (The Introduction): Discuss the car's design language, its era, or the philosophy behind its creation. "
        "Maintain a sophisticated tone. End with a thread indicator (e.g., 🧵).\n"
        
        "Tweet 2 (The Engineering): Detail the technical specifications professionally. "
        "Focus on the engine architecture, displacement, horsepower, or unique mechanical innovations. "
        "Use clean formatting (e.g., 'Engine: 3.9L V8 | Output: 471 hp'). Avoid excessive emojis.\n"
        
        "Tweet 3 (The Legacy): Analyze its impact on the automotive industry or its status in modern collecting. "
        "Why does this machine matter today? Conclude with 3 relevant, specific hashtags.\n\n"
        
        "Formatting Constraints:\n"
        "- Separate tweets strictly with '|||'.\n"
        "- Max 260 characters per tweet.\n"
        "- Tone: Professional, authoritative, appreciative."
    )

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        parts = [p.strip() for p in text.split('|||') if p.strip()]
        return parts
    except Exception as e:
        print(f"   ⚠️ Gemini Error: {e}")
        return []

# --- 📸 IMAGES (ROBUST MULTI-IMAGE FETCH) ---
def get_google_images(car_name):
    """
    Fetches up to 4 high-quality images for the car using Google Custom Search.
    Includes User-Agent headers to avoid 403 blocks.
    """
    # Refined query for professional/press-style photos
    query = f"{car_name} car press kit wallpaper 4k"
    print(f"   📸 Searching Google Images for: {query}")

    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        'q': query,
        'cx': SEARCH_ENGINE_ID,
        'key': GOOGLE_SEARCH_API_KEY,
        'searchType': 'image',
        'num': 8,  # Fetch extra to allow for filtering
        'fileType': 'jpg',
        'safe': 'active'
    }

    # Headers mimic a real browser to prevent blocking
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    downloaded_files = []

    try:
        resp = requests.get(url, params=params).json()
        items = resp.get('items', [])
        
        if not items: 
            print("   ⚠️ No images found.")
            return []

        for item in items:
            if len(downloaded_files) >= IMAGES_PER_TWEET:
                break
                
            image_url = item['link']
            try:
                # Download with timeout and headers
                img_resp = requests.get(image_url, headers=headers, timeout=10)
                
                # Check for valid image content (status 200 + sufficient size)
                if img_resp.status_code == 200 and len(img_resp.content) > 10000: # Min 10KB
                    f = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                    f.write(img_resp.content)
                    f.close()
                    downloaded_files.append(f.name)
                    print(f"   ✅ Downloaded: {image_url[:60]}...")
            except Exception as e:
                # Silently skip bad images
                continue

    except Exception as e:
        print(f"   ⚠️ Google Search API Error: {e}")
    
    return downloaded_files

# --- 🚀 POSTING LOGIC (GALLERY THREADS) ---
def post_thread(client_v2, api_v1, tweets, image_paths=[]):
    """
    Posts a thread. Attaches up to 4 images to the first tweet as a gallery.
    """
    first_tweet_id = None
    previous_tweet_id = None
    
    for i, text in enumerate(tweets):
        try:
            media_ids = []
            
            # Attach ALL images to the first tweet (Create a Gallery)
            if i == 0 and image_paths:
                print(f"   📤 Uploading {len(image_paths)} images to Twitter...")
                for img_path in image_paths:
                    try:
                        media = api_v1.media_upload(filename=img_path)
                        media_ids.append(media.media_id)
                    except Exception as e:
                        print(f"   ❌ Image upload failed for {img_path}: {e}")
                
                # Twitter limits to 4 media items per tweet
                media_ids = media_ids[:4]

            # Post the Tweet
            print(f"   🕊️ Posting Tweet {i+1}...")
            if i == 0:
                if media_ids:
                    resp = client_v2.create_tweet(text=text, media_ids=media_ids)
                else:
                    resp = client_v2.create_tweet(text=text)
                first_tweet_id = resp.data['id']
                previous_tweet_id = first_tweet_id
            else:
                # Reply to the previous tweet ID to create the thread
                resp = client_v2.create_tweet(text=text, in_reply_to_tweet_id=previous_tweet_id)
                previous_tweet_id = resp.data['id']
                
            # Smart Delay: Wait between tweets to ensure correct ordering
            time.sleep(5) 
            
        except Exception as e:
            print(f"   ❌ Error posting tweet {i+1}: {e}")
            return False

    return True

# --- 🏁 RUNNERS ---

def run_car_post(client_v2, api_v1, history):
    # Select a random car that hasn't been posted yet
    available_topics = [t for t in TOPICS if t not in history]
    if not available_topics:
        available_topics = TOPICS # Reset if all posted
        
    topic = random.choice(available_topics)
    print(f"   🏎️ Selected Car: {topic}")
    
    # 1. Get Images (Google Custom Search)
    img_paths = get_google_images(topic)
    
    # 2. Get Written Content (Gemini)
    tweet_parts = generate_content(topic)
    if not tweet_parts: 
        print("   ⚠️ Content generation failed.")
        return False
    
    # 3. Post Thread
    success = post_thread(client_v2, api_v1, tweet_parts, img_paths)
    
    # Cleanup temp files
    for p in img_paths:
        if os.path.exists(p): os.remove(p)
        
    if success:
        save_history(topic)
        print("   ✅ Car Thread Posted Successfully.")
    return success

def run():
    print("--- 🤖 SUPER CAR BOT INITIATED ---")
    
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
