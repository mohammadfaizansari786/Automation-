import tweepy
import os
import sys
import json
import datetime
import time
import random
import requests
import textwrap

# --- CONFIGURATION ---
DAILY_LIMIT = 18
# Try up to 5 times to find a topic with a good image
MAX_RETRIES = 5 

# --- HEADERS ---
WIKI_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# --- 🧠 PROFESSIONAL KNOWLEDGE BASE ---
TOPICS = {
    "CARS": [
        "McLaren F1", "Ferrari F40", "Porsche 959", "Bugatti Veyron", "Bugatti Chiron",
        "Ferrari LaFerrari", "Porsche 918 Spyder", "McLaren P1", "Pagani Zonda",
        "Pagani Huayra", "Koenigsegg Agera", "Rimac Nevera", "Aston Martin Valkyrie",
        "Mercedes-AMG One", "Lexus LFA", "Ford GT", "Maserati MC12", "Ferrari Enzo",
        "Lamborghini Veneno", "Lamborghini Sesto Elemento", "Bugatti EB110", "Jaguar XJ220",
        "Nissan Skyline GT-R R32", "Nissan Skyline GT-R R33", "Nissan Skyline GT-R R34",
        "Toyota Supra A80", "Mazda RX-7 FD", "Honda NSX (first generation)", "Subaru Impreza 22B",
        "Mitsubishi Lancer Evolution VI", "Nissan Silvia S15", "Toyota AE86", "Mazda 787B",
        "Toyota 2000GT", "Datsun 240Z", "Honda S2000", "Mitsubishi 3000GT VR-4",
        "Ferrari 250 GTO", "Lamborghini Countach", "Lamborghini Miura", "Lamborghini Diablo",
        "Mercedes-Benz 300 SL", "Jaguar E-Type", "Aston Martin DB5", "BMW 507",
        "Shelby Cobra", "Ford GT40", "Dodge Viper GTS", "Plymouth Superbird",
        "Chevrolet Corvette C2", "Pontiac GTO", "Dodge Charger Daytona", "Hemi Cuda",
        "Lancia Stratos", "Audi Quattro", "Lancia Delta Integrale", "Porsche 911 Carrera RS 2.7",
        "BMW M3 E30", "Mercedes-Benz 190E 2.5-16 Evolution II", "Renault 5 Turbo",
        "Porsche Carrera GT", "Alfa Romeo 8C Competizione", "Ford Mustang Shelby GT350R",
        "Dodge Challenger SRT Demon", "Nissan GT-R Nismo", "Ferrari 458 Speciale",
        "Lamborghini Murciélago SV", "Aston Martin One-77", "Koenigsegg Jesko"
    ],
    "TECH": [
        "W16 engine", "V12 engine", "Turbocharger", "Supercharger", "VTEC",
        "Dual-clutch transmission", "Limited-slip differential", "Monocoque",
        "Active aerodynamics", "KERS", "Carbon-ceramic brakes", "Regenerative braking",
        "Desmodromic valves", "Dry sump", "Ground effect (cars)", "Torque vectoring",
        "Flat-six engine", "Rotary engine", "Pushrod suspension", "Multilink suspension",
        "Space frame chassis", "Transaxle", "Variable valve timing", "Direct injection",
        "Sequential manual transmission", "Halo (safety device)", "DRS (Drag Reduction System)",
        "Double wishbone suspension", "Intercooler", "Exhaust manifold", "Camshaft",
        "Crankshaft", "Differential (mechanical device)", "Traction control system"
    ],
    "LEGENDS": [
        "Ayrton Senna", "Michael Schumacher", "Lewis Hamilton", "Juan Manuel Fangio",
        "Jim Clark", "Alain Prost", "Niki Lauda", "Jackie Stewart", "Stirling Moss",
        "Sebastian Vettel", "Fernando Alonso", "Max Verstappen", "Kimi Räikkönen",
        "Colin McRae", "Sébastien Loeb", "Ken Block", "Michele Mouton", "Tom Kristensen",
        "Dale Earnhardt", "Richard Petty", "Jeff Gordon", "Mario Andretti", "A.J. Foyt",
        "Enzo Ferrari", "Ferruccio Lamborghini", "Horacio Pagani", "Gordon Murray",
        "Adrian Newey", "Colin Chapman", "Carroll Shelby"
    ],
    "CIRCUITS": [
        "Nürburgring", "Circuit de la Sarthe", "Circuit de Monaco", "Silverstone Circuit",
        "Circuit de Spa-Francorchamps", "Suzuka International Racing Course", "Mount Panorama Circuit",
        "Indianapolis Motor Speedway", "Daytona International Speedway", "Laguna Seca",
        "Autodromo Nazionale di Monza", "Interlagos Circuit", "Pikes Peak International Hill Climb",
        "Goodwood Circuit", "Circuit of the Americas", "Red Bull Ring", "Hockenheimring",
        "Brands Hatch", "Imola Circuit", "Zandvoort Circuit"
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

# --- AUTHENTICATION ---
def get_clients():
    if not API_KEY or not API_SECRET:
        print("❌ Error: API Keys missing.")
        sys.exit(1)
    client_v2 = tweepy.Client(consumer_key=API_KEY, consumer_secret=API_SECRET, access_token=ACCESS_TOKEN, access_token_secret=ACCESS_SECRET)
    auth = tweepy.OAuth1UserHandler(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET)
    api_v1 = tweepy.API(auth)
    return client_v2, api_v1

# --- WIKI FETCHING ---
def get_wiki_data(topic):
    try:
        url = "https://en.wikipedia.org/w/api.php"
        # Increased pithumbsize to 1200 for HD images
        params = {
            "action": "query", "format": "json", "prop": "extracts|pageimages",
            "titles": topic, "pithumbsize": 1200, "exintro": 1, "explaintext": 1, "redirects": 1
        }
        response = requests.get(url, params=params, headers=WIKI_HEADERS, timeout=15)
        data = response.json()
        pages = data.get("query", {}).get("pages", {})
        
        for page_id, page_data in pages.items():
            if page_id == "-1": return None
            return {
                "title": page_data.get("title", topic),
                "text": page_data.get("extract", "").strip(),
                "image_url": page_data.get("thumbnail", {}).get("source", None),
                "url": f"https://en.wikipedia.org/wiki/{page_data.get('title', topic).replace(' ', '_')}"
            }
    except Exception as e:
        print(f"⚠️ Wiki Error: {e}")
    return None

def download_image(image_url):
    if not image_url: return None
    try:
        response = requests.get(image_url, headers=WIKI_HEADERS, stream=True, timeout=15)
        if response.status_code == 200:
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp:
                for chunk in response.iter_content(1024): temp.write(chunk)
                return temp.name
    except: pass
    return None

# --- STATE MANAGEMENT ---
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

# =========================================
# 📚 ENCYCLOPEDIA MODE (With Image Enforcer)
# =========================================
def run_encyclopedia_mode(client_v2, api_v1, history):
    print("   📚 Running Pro-Encyclopedia Mode...")
    
    # Weights: Focus heavily on Visuals (Cars/Circuits) but keep Legends/Tech
    cat_keys = ["CARS", "TECH", "LEGENDS", "CIRCUITS"]
    cat_weights = [40, 20, 20, 20]
    
    # Retry Loop to ensure we get an Image
    selected_data = None
    selected_cat = None
    
    for attempt in range(MAX_RETRIES):
        cat = random.choices(cat_keys, weights=cat_weights)[0]
        
        available = [t for t in TOPICS[cat] if t not in history]
        if not available: available = TOPICS[cat] # Reset if exhausted
        
        topic = random.choice(available)
        print(f"   🔍 Attempt {attempt+1}/{MAX_RETRIES}: Checking '{topic}'...")
        
        data = get_wiki_data(topic)
        
        # QUALITY CHECK: Must have text AND Image
        if data and data['text'] and data['image_url']:
            selected_data = data
            selected_cat = cat
            break
        else:
            print("      ❌ Missing image or text. Skipping.")
    
    if not selected_data:
        print("   ⚠️ Could not find a topic with an image after retries. Aborting run.")
        return False

    # Formatting Guidelines
    if selected_cat == "CARS":
        icon = "🏎️"
        tags = "#CarCulture #Automotive #DreamGarage"
    elif selected_cat == "TECH":
        icon = "⚙️"
        tags = "#Engineering #AutomotiveTech #Mechanics"
    elif selected_cat == "LEGENDS":
        icon = "🏆"
        tags = "#MotorsportLegend #F1 #RacingHistory"
    elif selected_cat == "CIRCUITS":
        icon = "🏁"
        tags = "#Racetrack #Motorsport #TrackDay"

    safe_title = "".join(x for x in selected_data['title'] if x.isalnum())
    
    # --- TWEET 1: VISUAL HOOK ---
    # We enforce a clean 240 char limit for professionalism
    chunks = textwrap.wrap(selected_data['text'], 240)
    intro = chunks[0]
    
    tweet1 = f"{icon} {selected_data['title'].upper()}\n\n{intro}\n\n🧵 Thread 👇\n#{safe_title} {tags}"

    # Handle Image Download
    media_id = None
    if selected_data['image_url']:
        path = download_image(selected_data['image_url'])
        if path:
            try:
                media = api_v1.media_upload(filename=path)
                media_id = media.media_id
                os.remove(path)
            except: pass

    try:
        # Post Main Tweet
        print(f"   📝 Posting: {selected_data['title']}...")
        if media_id:
            t1 = client_v2.create_tweet(text=tweet1, media_ids=[media_id])
        else:
            # Fallback (should rarely happen due to retry loop)
            t1 = client_v2.create_tweet(text=tweet1)
        
        reply_id = t1.data['id']
        
        # --- THREAD: DETAILS ---
        # Post up to 3 detail tweets
        for chunk in chunks[1:4]:
            time.sleep(2) 
            reply = client_v2.create_tweet(text=chunk, in_reply_to_tweet_id=reply_id)
            reply_id = reply.data['id']
            
        # --- FINAL TWEET: SOURCE ---
        final_text = f"📖 Source & Details: {selected_data['url']}"
        client_v2.create_tweet(text=final_text, in_reply_to_tweet_id=reply_id)

        save_history(selected_data['title']) # Save title to avoid repeats
        print(f"   ✅ Successfully posted professional thread for {selected_data['title']}")
        return True

    except Exception as e:
        print(f"   ❌ Post Failed: {e}")
        return False

# --- MAIN RUNNER ---
def run():
    print("--- 🤖 Pro-Bot Starting ---")
    
    state = get_daily_state()
    print(f"📊 Daily Count: {state['count']}/{DAILY_LIMIT}")

    if state["count"] >= DAILY_LIMIT:
        print("⛔ Daily limit reached.")
        return

    client_v2, api_v1 = get_clients()
    history = load_history()
    
    success = run_encyclopedia_mode(client_v2, api_v1, history)
    
    if success:
        update_state(state["count"] + 1)

if __name__ == "__main__":
    run()
    
