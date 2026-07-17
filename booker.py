import requests
import time
import os
from datetime import datetime

# ==========================================
# 1. YOUR DETAILS (Now loaded securely from GitHub Secrets)
# ==========================================
EMAIL = os.environ.get("EMAIL")
PASSWORD = os.environ.get("PASSWORD")
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK_URL")

TARGET_DATE = "2026-07-24"

# ==========================================
# 2. YOUR PRIORITY RULES
# ==========================================
PRIORITY_RULES = [
    {"location": "hyde-park-courts", "start": "19:00", "end": "21:00"},         # Generates 19:00, 20:00, 21:00
    {"location": "the-regents-park-courts", "start": "19:00", "end": "21:00"},  # Generates 19:00, 20:00, 21:00
    {"location": "the-regents-park-courts", "start": "12:00", "end": "15:00"}   # Generates 12:00, 13:00, 14:00, 15:00
]

# ==========================================
# 3. AUTHENTICATION LOGIC
# ==========================================
def auto_login():
    """Logs into the website and returns a fresh Bearer Token."""
    if not EMAIL or not PASSWORD:
        print("❌ EMAIL or PASSWORD missing from GitHub Secrets!")
        return None
        
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Authenticating as {EMAIL}...")
    
    # NOTE: If the login fails, check your Network tab and update this URL and payload
    login_url = "https://flow.onl/api/login" 
    payload = {
        "email": EMAIL,
        "password": PASSWORD
    }
    
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "origin": "https://sportsandleisureroyalparks.bookings.flow.onl",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        resp = requests.post(login_url, json=payload, headers=headers)
        
        if resp.status_code in [200, 201]:
            data = resp.json()
            # The token is usually nested in the response. We check a few common locations.
            token = data.get("token") or data.get("access_token") or data.get("data", {}).get("token")
            if token:
                print("✅ Successfully logged in and generated fresh token!")
                return token
                
        print(f"❌ Login failed. Status: {resp.status_code}")
        print(f"Server response: {resp.text[:200]}")
        return None
        
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None


# ==========================================
# 4. THE BOOKER LOGIC
# ==========================================
def expand_priority_rules(rules):
    queue = []
    for rule in rules:
        start_hour = int(rule["start"].split(":")[0])
        end_hour = int(rule["end"].split(":")[0])
        
        for hour in range(start_hour, end_hour + 1):
            time_str = f"{hour:02d}:00" 
            queue.append({"location": rule["location"], "time": time_str})
            
    return queue

def get_base_headers(token):
    return {
        "accept": "application/json",
        "authorization": f"Bearer {token}",
        "origin": "https://sportsandleisureroyalparks.bookings.flow.onl",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

def send_alert(msg):
    if DISCORD_WEBHOOK:
        requests.post(DISCORD_WEBHOOK, json={"content": msg})

def hunt_for_court():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Booker Started.")
    
    # 1. Automate the Login
    bearer_token = auto_login()
    if not bearer_token:
        print("Stopping script because login failed.")
        return
        
    print(f"\nTarget Date: {TARGET_DATE}")
    
    priority_queue = expand_priority_rules(PRIORITY_RULES)
    
    print("Strict Priority Queue (Auto-Generated):")
    for i, p in enumerate(priority_queue, 1):
        print(f"  {i}. {p['location']} @ {p['time']}")
    print("-" * 30)
        
    headers = get_base_headers(bearer_token)
    locations_to_check = list(set([p["location"] for p in priority_queue]))
    
    while True:
        try:
            available_slots = {}
            for slug in locations_to_check:
                url = f"https://flow.onl/api/activities/venue/{slug}/activity/tennis/v2/times"
                resp = requests.get(url, headers=headers, params={"date": TARGET_DATE})
                
                if resp.status_code == 200:
                    slots = resp.json().get("data", [])
                    available_slots[slug] = {}
                    for slot in slots:
                        if slot.get("action_to_show", {}).get("status") == "BOOK":
                            time_val = slot.get("starts_at", {}).get("format_24_hour")
                            if time_val:
                                available_slots[slug][time_val] = slot.get("composite_key")

            # Check strictly in the generated order
            for target in priority_queue:
                loc = target["location"]
                time_req = target["time"]
                
                if loc in available_slots and time_req in available_slots[loc]:
                    composite_key = available_slots[loc][time_req]
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] MATCH FOUND: {loc} at {time_req}! Securing...")
                    
                    success = book_court(composite_key, loc, time_req, headers)
                    if success:
                        return 
                        
            time.sleep(0.5)
            
        except Exception as e:
            print(f"Error checking availability: {e}")
            time.sleep(1)

def book_court(composite_key, slug, time_won, headers):
    details_url = f"https://flow.onl/api/activities/venue/{slug}/activity/tennis/v2/times/{composite_key}"
    
    try:
        resp = requests.get(details_url, headers=headers, params={"date": TARGET_DATE})
        courts = resp.json().get("data", [])
        
        target_court_id = None
        for court in courts:
            if court.get("action_to_show", {}).get("status") == "BOOK":
                target_court_id = court.get("id")
                break
                
        if not target_court_id:
            print(f"Failed to isolate a physical court for {time_won}.")
            return False

        cart_url = "https://flow.onl/api/activities/cart/add"
        payload = {
            "items": [{
                "id": target_court_id,
                "type": "purchasableOccurrence",
                "pricing_option_id": 3871, 
                "apply_benefit": True,
                "activity_restriction_ids": []
            }],
            "membership_user_id": None,
            "selected_user_id": None
        }
        
        cart_resp = requests.post(cart_url, headers=headers, json=payload)
        
        if cart_resp.status_code == 200:
            print(f"🚨 SUCCESS! {slug} @ {time_won} ADDED TO CART! 🚨")
            msg = (
                f"🚨 **COURT SECURED IN CART!** 🚨\n"
                f"**Location:** {slug}\n"
                f"**Date:** {TARGET_DATE}\n"
                f"**Time:** {time_won}\n"
                f"**Checkout Link:** <https://sportsandleisureroyalparks.bookings.flow.onl/cart>\n"
                f"*You have 10 minutes to pay!*"
            )
            send_alert(msg)
            return True
        else:
            print(f"Failed to add to cart. Status: {cart_resp.status_code}")
            return False
            
    except Exception as e:
        print(f"Booking error: {e}")
        return False

if __name__ == "__main__":
    hunt_for_court()
