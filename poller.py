import requests
import os
from datetime import datetime

# ==========================================
# CONFIGURATION
# ==========================================
LOCATIONS = {
    "Hyde Park": "hyde-park-courts",
    "Regent's Park": "the-regents-park-courts"
}

# The date you are hunting for
TARGET_DATE = "2026-07-24" 

HEADERS = {
    "accept": "application/json",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def poll_courts():
    print(f"Running poll at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
    
    all_available_slots = {}
    
    for name, slug in LOCATIONS.items():
        # FIX: Added the full 'sportsandleisureroyalparks.bookings' subdomain here
        api_url = f"https://sportsandleisureroyalparks.bookings.flow.onl/api/activities/venue/{slug}/activity/tennis/v2/times"
        params = {"date": TARGET_DATE}
        
        HEADERS["referrer"] = f"https://sportsandleisureroyalparks.bookings.flow.onl/location/{slug}/tennis/{TARGET_DATE}/by-time"
        
        try:
            response = requests.get(api_url, headers=HEADERS, params=params)
            
            if response.status_code != 200:
                print(f"Error: API returned status {response.status_code} for {name}")
                continue

            json_response = response.json()
            available_slots = []
            
            for slot in json_response.get("data", []):
                status = slot.get("action_to_show", {}).get("status", "")
                
                if status == "BOOK":
                    time = slot.get("starts_at", {}).get("format_24_hour", "Unknown Time")
                    available_slots.append(time)

            if available_slots:
                print(f"✅ SLOTS FOUND at {name}: {', '.join(available_slots)}")
                all_available_slots[name] = available_slots
            else:
                print(f"❌ No slots available at {name}.")
                
        except Exception as e:
            print(f"Script failed for {name}: {e}")

    if all_available_slots:
        send_telegram_alert(all_available_slots)


def send_telegram_alert(available_data):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("Telegram credentials missing. Set them in GitHub Secrets to receive phone alerts.")
        return

    msg_lines = [f"🎾 Tennis Courts Available! ({TARGET_DATE})\n"]
    
    for location, slots in available_data.items():
        slug = LOCATIONS[location]
        booking_link = f"https://sportsandleisureroyalparks.bookings.flow.onl/location/{slug}/tennis/{TARGET_DATE}/by-time"
        
        msg_lines.append(f"📍 {location}: {', '.join(slots)}")
        msg_lines.append(f"🔗 {booking_link}\n")

    msg = "\n".join(msg_lines)
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    requests.post(url, json={"chat_id": chat_id, "text": msg})

if __name__ == "__main__":
    poll_courts()
