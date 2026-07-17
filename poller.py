import requests
import os
from datetime import datetime

# The URL you extract from Chrome's Network tab
API_URL = "https://sportsandleisureroyalparks.bookings.flow.onl/api/availability_placeholder"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

PARAMS = {
    "date": "2026-07-24",
    "location": "hyde-park-courts"
}

def poll_courts():
    print(f"Running poll at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
    
    try:
        response = requests.get(API_URL, headers=HEADERS, params=PARAMS)
        
        if response.status_code != 200:
            print(f"Error: API returned status {response.status_code}")
            return

        data = response.json()
        print("Successfully fetched data from API. Here is the raw response:")
        print(data) # This prints to GitHub logs so you can see the structure
        
        # We will add the logic to parse 'data' and send a Telegram alert 
        # once you run this the first time and see how the website formats its timeslots.
            
    except Exception as e:
        print(f"Script failed: {e}")

if __name__ == "__main__":
    poll_courts()
