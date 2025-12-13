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
DAILY_LIMIT = 16

# --- TOPICS (Encyclopedia Mode) ---
TOPICS = {
    "LEGENDARY_CARS": [
        "McLaren F1", "Ferrari F40", "Porsche 959", "Bugatti Chiron", "Pagani Huayra",
        "Lexus LFA", "Ford GT40", "Ferrari Enzo", "Nissan Skyline GT-R R34", "Mazda 787B",
        "Lamborghini Countach", "Mercedes 300SL Gullwing", "Aston Martin Valkyrie", 
        "Koenigsegg Jesko", "BMW E38", "Lancia Stratos", "Audi Quattro S1"
    ],
    "CAR_TECH": [
        "W16 Engine configuration", "Naturally Aspirated V12", "Variable Geometry Turbocharger", 
        "Dual-clutch transmission mechanics", "Active Aerodynamics systems", "F1 KERS System", 
        "Carbon-Ceramic Brakes utility", "Pushrod vs Pullrod Suspension", "Rotary (Wankel) Engine",
        "Limited Slip Differential (LSD)", "Ground Effect aerodynamics", "Dry Sump Lubrication"
    ],
    "DRIVERS": [
        "Ayrton Senna", "Michael Schumacher", "Lewis Hamilton", "Niki Lauda", 
        "Jim Clark", "Alain Prost", "Juan Manuel Fangio", "Ken Block", 
        "Colin McRae", "Michele Mouton", "Max Verstappen", "Yuki Tsunoda"
    ],
    "RACETRACKS": [
        "Nürburgring Nordschleife", "Circuit de Monaco", "Spa-Francorchamps", 
        "Suzuka Circuit", "Le Mans (Circuit de la Sarthe)", "Mount Panorama (Bathurst)", 
        "Silverstone Circuit", "Laguna Seca (The Corkscrew)", "Monza"
    ]
}

# --- AUTHENTICATION ---
api_key = os.getenv("API_KEY")
api_secret = os.getenv("API_SECRET")
access_token = os.getenv("ACCESS_TOKEN")
access_secret = os.getenv("ACCESS_SECRET")

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
UNSPLASH_KEY = os.getenv("UNSPLASH_ACCESS_KEY")

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
def generate_content(mode, topic_data):
    """
    Generates text using Gemini. 
    Returns a LIST of strings. If it's a thread, it returns [tweet1, tweet2, tweet3].
    """
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    if mode == "CAR_TECH":
        # Tech needs details -> Thread
        prompt = (
            f"Write a 3-tweet educational thread about '{topic_data}'. "
            "Tweet 1: Hook and basic definition. "
            "Tweet 2: How it works technically (engineering focus). "
            "Tweet 3: Why it is important for performance. "
            "Separate each tweet strictly with '|||'. Keep each under 240 chars."
        )
    elif mode == "LEGENDARY_CARS":
        # Cars need history -> Thread
        prompt = (
            f"Write a 3-tweet thread admiring the legendary '{topic_data}'. "
            "Tweet 1: The legacy and visual appeal. "
            "Tweet 2: Engine specs and performance stats. "
            "Tweet 3: Why it is an icon today. "
            "Separate each tweet strictly with '|||'. Keep each under 240 chars."
        )
    elif mode == "DRIVERS":
        prompt = (
            f"Write a 2-tweet tribute to racing driver '{topic_data}'. "
            "Tweet 1: Their status and driving style. "
            "Tweet 2: Their most famous achievement or championship. "
            "Separate each tweet strictly with '|||'. Keep each under 240 chars."
        )
    else: # RACETRACKS or general
        prompt = (
            f"Write a professional, exciting tweet (under 240 chars) about the race track '{topic_data}'. "
            "Mention its most famous corner. Include 2 hashtags."
        )

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        # Split by delimiter to get thread parts
        parts = [p.strip() for p in text.split('|||') if p.strip()]
        return parts
    except Exception as e:
        print(f"   ⚠️ Gemini Error: {e}")
        return []

# --- 📸 IMAGES (UNSPLASH) ---
def get_unsplash_image(query):
    if not UNSPLASH_KEY: return None, None
    
    # Improve query for better results
    search_query = f"{query} automotive wallpaper"
    print(f"   📸 Searching Unsplash for: {search_query}")
    
    try:
        url = f"https://api.unsplash.com/search/photos?query={search_query}&per_page=1&orientation=landscape&client_id={UNSPLASH_KEY}"
        resp = requests.get(url).json()
        if resp['results']:
            result = resp['results'][0]
            image_url = result['urls']['regular']
            photographer = result['user']['name']
            
            # Download
            img_data = requests.get(image_url).content
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                f.write(img_data)
                return f.name, photographer
    except Exception as e:
        print(f"   ⚠️ Unsplash Error: {e}")
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
                print("   📤 Uploading media...")
                media = api_v1.media_upload(filename=image_path)
                media_ids = [media.media_id]
                # Add credit to text if fits
                if image_credit:
                    credit_text = f" 📸 {image_credit}"
                    if len(text) + len(credit_text) < 280:
                        text += credit_text

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

def run_encyclopedia_post(client_v2, api_v1, history):
    # Pick Category & Topic
    cat = random.choice(list(TOPICS.keys()))
    topic = random.choice([t for t in TOPICS[cat] if t not in history] or TOPICS[cat])
    
    print(f"   📚 Topic ({cat}): {topic}")
    
    # 1. Get Image
    img_path, credit = get_unsplash_image(topic)
    
    # 2. Get Thread Content
    tweet_parts = generate_content(cat, topic)
    if not tweet_parts: return False
    
    # 3. Post
    success = post_thread(client_v2, api_v1, tweet_parts, img_path, credit)
    
    if img_path and os.path.exists(img_path):
        os.remove(img_path)
        
    if success:
        save_history(topic)
        print("   ✅ Encyclopedia Thread Posted.")
    return success

def run():
    print("--- 🤖 SUPER-BOT INITIATED ---")
    
    state = get_daily_state()
    if state["count"] >= DAILY_LIMIT:
        print("⛔ Daily limit reached.")
        return

    client_v2, api_v1 = get_clients()
    history = load_history()
    
    # 100% Encyclopedia Mode (No News)
    success = run_encyclopedia_post(client_v2, api_v1, history)
        
    if success:
        update_state(state["count"] + 1)

if __name__ == "__main__":
    run()

