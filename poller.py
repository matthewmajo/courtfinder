import requests
import os
from datetime import datetime

# The actual API endpoint you found
API_URL = "https://flow.onl/api/activities/venue/hyde-park-courts/activity/tennis/v2/times"

# We use the headers from your fetch request to look like a real browser
HEADERS = {
    "accept": "application/json",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
    "referrer": "https://sportsandleisureroyalparks.bookings.flow.onl/location/hyde-park-courts/tennis/2026-07-24/by-time",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# The date to check
PARAMS = {
    "date": "2026-07-24"
}

def poll_courts():
    print(f"Running poll at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
    
    try:
        response = requests.get(API_URL, headers=HEADERS, params=PARAMS)
        
        if response.status_code != 200:
            print(f"Error: API returned status {response.status_code}")
            return

        json_response = response.json()
        available_slots = []
        
        # Loop through the 'data' array in the JSON response
        for slot in json_response.get("data", []):
            status = slot.get("action_to_show", {}).get("status", "")
            
            # If the status is BOOK, it means the court is available
            if status == "BOOK":
                # Extract the 24-hour time (e.g., "14:00")
                time = slot.get("starts_at", {}).get("format_24_hour", "Unknown Time")
                available_slots.append(time)

        if available_slots:
            print(f"✅ AVAILABLE SLOTS FOUND: {', '.join(available_slots)}")
            send_telegram_alert(available_slots)
        else:
            print("❌ No slots available right now.")
            
    except Exception as e:
        print(f"Script failed: {e}")

def send_telegram_alert(slots):
    # Pulls the secure credentials you saved in GitHub Secrets
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("Telegram credentials missing. Set them in GitHub Secrets to receive phone alerts.")
        return

    formatted_slots = ", ".join(slots)
    msg = f"🎾 Tennis Court Available!\n\nDate: {PARAMS['date']}\nSlots: {formatted_slots}\n\nBook here: {HEADERS['referrer']}"
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    requests.post(url, json={"chat_id": chat_id, "text": msg})

if __name__ == "__main__":
    poll_courts()
