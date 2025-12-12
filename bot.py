import tweepy
import os
import sys
import json
import datetime
import time
import random
import requests
import tempfile
import textwrap

# --- CONFIGURATION ---
DAILY_LIMIT = 16  # Safe for Free Tier
POSTS_PER_RUN = 1 

# --- HEADERS (Crucial: Prevents Wiki from blocking you) ---
WIKI_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# --- 🧠 THE LIBRARY OF EVERYTHING ---
QUOTES_DATA = [
    ("Aerodynamics are for people who can't build engines.", "Enzo Ferrari"),
    ("If you no longer go for a gap that exists, you are no longer a racing driver.", "Ayrton Senna"),
    ("Speed has never killed anyone, suddenly becoming stationary... that’s what gets you.", "Jeremy Clarkson"),
    ("To finish first, you must first finish.", "Juan Manuel Fangio"),
    ("Straight roads are for fast cars, turns are for fast drivers.", "Colin McRae"),
    ("I don’t drive to get from A to B. I enjoy feeling the car’s reactions, becoming part of it.", "Enzo Ferrari"),
    ("When I see a curve, I don’t think about the curve. I think about how I can get out of it.", "Gilles Villeneuve"),
    ("Racing is life. Anything before or after is just waiting.", "Steve McQueen"),
    ("You win some, lose some, and wreck some.", "Dale Earnhardt"),
    ("Adding power makes you faster on the straights. Subtracting weight makes you faster everywhere.", "Colin Chapman"),
    ("The winner ain’t the one with the fastest car, it’s the one who refuses to lose.", "Dale Earnhardt"),
    ("Simplify, then add lightness.", "Colin Chapman"),
    ("I am not designed to come second or third. I am designed to win.", "Ayrton Senna"),
    ("Race cars are neither beautiful nor ugly. They become beautiful when they win.", "Enzo Ferrari"),
    ("Second place is just the first of the losers.", "Enzo Ferrari")
]

# Simple list of names for Poll Distractors
LEGEND_NAMES = list(set([q[1] for q in QUOTES_DATA] + [
    "Niki Lauda", "James Hunt", "Lewis Hamilton", "Michael Schumacher", 
    "Carroll Shelby", "Ken Miles", "Adrian Newey", "Christian Horner"
]))

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
        "Sequential manual transmission", "Halo (safety device)", "DRS (Drag Reduction System)"
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

    client_v2 = tweepy.Client(
        consumer_key=API_KEY,
        consumer_secret=API_SECRET,
        access_token=ACCESS_TOKEN,
        access_token_secret=ACCESS_SECRET
    )

    auth = tweepy.OAuth1UserHandler(API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET)
    api_v1 = tweepy.API(auth)

    return client_v2, api_v1

# --- WIKI FETCHING (SAFE MODE) ---
def get_wiki_data(topic):
    try:
        url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query", "format": "json", "prop": "extracts|pageimages",
            "titles": topic, "pithumbsize": 1000, "exintro": 1, "explaintext": 1, "redirects": 1
        }
        
        # ADDED HEADERS HERE TO MIMIC BROWSER
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
        print(f"⚠️ Wiki Fetch Error: {e}")
        return None
    return None

def download_image(image_url):
    if not image_url: return None
    try:
        # ADDED HEADERS HERE TOO
        response = requests.get(image_url, headers=WIKI_HEADERS, stream=True, timeout=15)
        if response.status_code == 200:
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
# ⚔️ MODE 1: VERSUS BATTLE
# =========================================
def run_versus_mode(client_v2, api_v1, history):
    print("   ⚔️ Running VS Battle Mode...")
    candidates = random.sample(TOPICS["CARS"], 2)
    car1 = get_wiki_data(candidates[0])
    car2 = get_wiki_data(candidates[1])
    
    if not car1 or not car2: return False
    
    text = f"⚔️ HEAD-TO-HEAD BATTLE ⚔️\n\n🔴 {car1['title']}\n      VS\n🔵 {car2['title']}\n\nWhich keys are you grabbing? 🤔\n#CarBattle #Versus #{car1['title'].replace(' ','')} #{car2['title'].replace(' ','')}"
    
    media_ids = []
    for c in [car1, car2]:
        if c['image_url']:
            path = download_image(c['image_url'])
            if path:
                try:
                    media = api_v1.media_upload(filename=path)
                    media_ids.append(media.media_id)
                    os.remove(path)
                except: pass
    
    try:
        if media_ids:
            t1 = client_v2.create_tweet(text=text, media_ids=media_ids)
        else:
            t1 = client_v2.create_tweet(text=text)
            
        reply_text = f"📊 TALE OF THE TAPE:\n\n1️⃣ {car1['title']}: {textwrap.shorten(car1['text'], 100)}\n\n2️⃣ {car2['title']}: {textwrap.shorten(car2['text'], 100)}\n\n👇 Vote in the replies!"
        client_v2.create_tweet(text=reply_text, in_reply_to_tweet_id=t1.data['id'])
        
        save_history(f"vs_{candidates[0]}_{candidates[1]}")
        print("   ✅ Battle Posted.")
        return True
    except Exception as e:
        print(f"   ❌ Battle Failed: {e}")
        return False

# =========================================
# 📊 MODE 2: QUOTE POLL
# =========================================
def run_quote_poll_mode(client_v2, history):
    print("   📊 Running Quote Quiz Mode...")
    
    target = random.choice(QUOTES_DATA)
    quote_text = target[0]
    correct_author = target[1]
    
    quote_id = f"quote_{hash(quote_text)}"
    if quote_id in history: return False
    
    distractors = [n for n in LEGEND_NAMES if n != correct_author]
    random.shuffle(distractors)
    choices = distractors[:3] + [correct_author]
    random.shuffle(choices) 
    
    try:
        text = f"🗣️ WHO SAID IT?\n\n\"{quote_text}\"\n\nVote below! 👇 #MotorsportQuiz #Quotes"
        client_v2.create_tweet(text=text, poll_options=choices[:4], poll_duration_minutes=1440)
        save_history(quote_id)
        print("   ✅ Quote Poll Posted.")
        return True
    except Exception as e:
        print(f"   ❌ Poll Failed: {e}")
        # Fallback if poll fails
        try:
            client_v2.create_tweet(text=f"“{quote_text}” — {correct_author}\n\n#Motorsport #Inspiration")
            save_history(quote_id)
            return True
        except: return False

# =========================================
# 📚 MODE 3: THE LIBRARY (Threaded)
# =========================================
def run_standard_mode(client_v2, api_v1, history):
    print("   📚 Running Library Mode...")
    
    cat_choices = ["CARS", "TECH", "LEGENDS", "CIRCUITS"]
    cat_weights = [50, 15, 20, 15]
    
    category = random.choices(cat_choices, weights=cat_weights)[0]
    available = [t for t in TOPICS[category] if t not in history]
    if not available: available = TOPICS[category]
    topic = random.choice(available)
    
    data = get_wiki_data(topic)
    if not data: return False

    if category == "CARS":
        hook = f"🏎️ ICONIC MACHINE: {data['title']}"
        tags = "#CarCulture #AutomotiveHistory #DreamGarage"
    elif category == "TECH":
        hook = f"⚙️ ENGINEERING: {data['title']}"
        tags = "#Engineering #CarTech #HowItWorks"
    elif category == "LEGENDS":
        hook = f"🏆 RACING LEGEND: {data['title']}"
        tags = "#Motorsport #F1 #Racing #Legend"
    elif category == "CIRCUITS":
        hook = f"🏁 SACRED GROUND: {data['title']}"
        tags = "#Racetrack #Motorsport #History"

    tweets = []
    safe_title = "".join(x for x in data['title'] if x.isalnum())
    
    tweets.append(f"{hook}\n\n{textwrap.shorten(data['text'], 160)}\n\n🧵 Thread below 👇\n#{safe_title} {tags}")
    
    chunks = textwrap.wrap(data['text'], 270)
    for c in chunks[:4]: 
        if c not in tweets[0]: tweets.append(c)
    tweets.append(f"📖 Full History: {data['url']}")

    media_id = None
    if data['image_url']:
        path = download_image(data['image_url'])
        if path:
            try:
                media = api_v1.media_upload(filename=path)
                media_id = media.media_id
                os.remove(path)
            except: pass

    try:
        prev_id = None
        for i, txt in enumerate(tweets):
            if i == 0:
                resp = client_v2.create_tweet(text=txt, media_ids=[media_id] if media_id else None)
            else:
                resp = client_v2.create_tweet(text=txt, in_reply_to_tweet_id=prev_id)
            prev_id = resp.data['id']
            # DELAY BETWEEN TWEETS IN THREAD (Humanizes typing speed)
            time.sleep(random.randint(5, 12)) 
        save_history(topic)
        print(f"   ✅ Posted {topic}")
        return True
    except Exception as e:
        print(f"   ❌ Library Post Failed: {e}")
        return False

# --- MAIN RUNNER ---
def run():
    print("--- 🤖 AutoLibrary Bot Starting ---")
    
    # 💤 CRITICAL: HUMANIZATION DELAY
    # Random sleep between 1 min and 15 mins
    # Prevents "Top of the Hour" robotic pattern
    delay = random.randint(60, 900)
    print(f"   💤 Sleeping for {delay} seconds to mimic human behavior...")
    time.sleep(delay)

    state = get_daily_state()
    print(f"📊 Daily Count: {state['count']}/{DAILY_LIMIT}")

    if state["count"] >= DAILY_LIMIT:
        print("⛔ Daily limit reached.")
        return

    client_v2, api_v1 = get_clients()
    history = load_history()
    
    # 🎲 DECIDE MODE
    # 15% Battle | 15% Quote Poll | 70% Thread
    dice = random.random()
    success = False
    
    if dice < 0.15:
        success = run_versus_mode(client_v2, api_v1, history)
    elif dice < 0.30:
        success = run_quote_poll_mode(client_v2, history)
    
    if not success:
        run_standard_mode(client_v2, api_v1, history)
        
    update_state(state["count"] + 1)

if __name__ == "__main__":
    run()
    
