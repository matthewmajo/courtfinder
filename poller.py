import requests
import os
import json
import time  # Fixed!
from datetime import datetime, timedelta

# ==========================================
# CONFIGURATION
# ==========================================
LOCATIONS = {
    "Hyde Park": "hyde-park-courts",
    "Regent's Park": "the-regents-park-courts"
}
STATE_FILE = "state.json"

def is_time_allowed(date_str, time_str):
    """Your custom time logic."""
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    weekday = date_obj.weekday() 
    hour = int(time_str.split(":")[0]) 
    
    if weekday in [5, 6]: # Sat, Sun
        return True
    elif weekday in [1, 2, 3]: # Tue, Wed, Thu
        return hour >= 20
    elif weekday in [0, 4]: # Mon, Fri
        return hour >= 19
    return False

# ==========================================
# MEMORY MANAGEMENT
# ==========================================
def load_memory():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def save_memory(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=4)

# ==========================================
# DISCORD INTERACTION
# ==========================================
def send_discord_msg(webhook_url, location, target_date, time_str, slug):
    url = webhook_url if "?wait=true" in webhook_url else f"{webhook_url}?wait=true"
    
    day_name = datetime.strptime(target_date, "%Y-%m-%d").strftime("%A")
    booking_link = f"https://sportsandleisureroyalparks.bookings.flow.onl/location/{slug}/tennis/{target_date}/by-time"
    
    msg = f"🎾 **NEW SLOT:** {location} | {day_name}, {target_date} @ **{time_str}**\n🔗 <{booking_link}>"
    
    resp = requests.post(url, json={"content": msg})
    if resp.status_code in [200, 201]:
        return resp.json().get("id")
    return None

def delete_discord_msg(webhook_url, message_id):
    base_url = webhook_url.split("?")[0] 
    delete_url = f"{base_url}/messages/{message_id}"
    requests.delete(delete_url)

# ==========================================
# MAIN LOGIC
# ==========================================
def poll_courts():
    print(f"Running stateful poll at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
    
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("Webhook missing, exiting.")
        return
        
    memory = load_memory()
    currently_available_keys = set()
    
    # Check 7 days ahead
    dates_to_check = [(datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(8)]
    
    for target_date in dates_to_check:
        for name, slug in LOCATIONS.items():
            api_url = f"https://flow.onl/api/activities/venue/{slug}/activity/tennis/v2/times"
            headers = {
                "accept": "application/json",
                "origin": "https://sportsandleisureroyalparks.bookings.flow.onl",
                "user-agent": "Mozilla/5.0"
            }
            
            try:
                response = requests.get(api_url, headers=headers, params={"date": target_date})
                if response.status_code == 200:
                    for slot in response.json().get("data", []):
                        if slot.get("action_to_show", {}).get("status") == "BOOK":
                            time_val = slot.get("starts_at", {}).get("format_24_hour")
                            if time_val and is_time_allowed(target_date, time_val):
                                unique_key = f"{name}|{target_date}|{time_val}"
                                currently_available_keys.add(unique_key)
            except Exception as e:
                print(f"Error checking {name}: {e}")

    # Process NEW slots
    for key in currently_available_keys:
        if key not in memory:
            print(f"✅ NEW SLOT FOUND: {key}")
            name, target_date, time_str = key.split("|")
            msg_id = send_discord_msg(webhook_url, name, target_date, time_str, LOCATIONS[name])
            if msg_id:
                memory[key] = msg_id
            time.sleep(1)
            
    # Process GONE slots
    for key in list(memory.keys()):
        if key not in currently_available_keys:
            print(f"❌ SLOT BOOKED: {key}")
            delete_discord_msg(webhook_url, memory[key])
            del memory[key]
            time.sleep(1)

    save_memory(memory)
    print("Poll complete. Memory saved.")

if __name__ == "__main__":
    poll_courts()
