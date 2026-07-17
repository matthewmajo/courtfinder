import requests
import os
from datetime import datetime, timedelta

# ==========================================
# CONFIGURATION
# ==========================================
LOCATIONS = {
    "Hyde Park": "hyde-park-courts",
    "Regent's Park": "the-regents-park-courts"
}

def is_time_allowed(date_str, time_str):
    """
    Checks if the available time slot matches your required schedule:
    - Sat/Sun: All day
    - Tue/Wed/Thu: 8 PM (20:00) onwards
    - Mon/Fri: 7 PM (19:00) onwards
    """
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    weekday = date_obj.weekday() # 0 = Mon, 6 = Sun
    hour = int(time_str.split(":")[0]) # Extracts the '14' from '14:00'
    
    if weekday in [5, 6]: 
        # Saturday, Sunday: All day
        return True
    elif weekday in [1, 2, 3]: 
        # Tuesday, Wednesday, Thursday: >= 20:00
        return hour >= 20
    elif weekday in [0, 4]: 
        # Monday, Friday: >= 19:00
        return hour >= 19
        
    return False

def poll_courts():
    print(f"Running poll at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
    
    # Generate a list of dates: Today + the next 7 days
    dates_to_check = [(datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(8)]
    
    # We now store data by date, then by location
    all_available_slots = {}
    
    for target_date in dates_to_check:
        day_name = datetime.strptime(target_date, "%Y-%m-%d").strftime("%A")
        
        for name, slug in LOCATIONS.items():
            api_url = f"https://flow.onl/api/activities/venue/{slug}/activity/tennis/v2/times"
            params = {"date": target_date}
            
            headers = {
                "accept": "application/json",
                "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
                "origin": "https://sportsandleisureroyalparks.bookings.flow.onl",
                "referer": f"https://sportsandleisureroyalparks.bookings.flow.onl/location/{slug}/tennis/{target_date}/by-time",
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-site",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            
            try:
                response = requests.get(api_url, headers=headers, params=params)
                
                if response.status_code != 200:
                    continue

                try:
                    json_response = response.json()
                except Exception:
                    print(f"❌ BLOCKED: Failed to parse JSON for {name} on {target_date}.")
                    continue
                
                available_slots = []
                
                for slot in json_response.get("data", []):
                    status = slot.get("action_to_show", {}).get("status", "")
                    
                    if status == "BOOK":
                        time = slot.get("starts_at", {}).get("format_24_hour", "Unknown Time")
                        
                        # Apply your custom time filters!
                        if time != "Unknown Time" and is_time_allowed(target_date, time):
                            available_slots.append(time)

                if available_slots:
                    print(f"✅ SLOTS FOUND: {name} | {target_date} ({day_name}) | {', '.join(available_slots)}")
                    
                    if target_date not in all_available_slots:
                        all_available_slots[target_date] = {}
                    all_available_slots[target_date][name] = available_slots
                    
            except Exception as e:
                print(f"Script failed for {name} on {target_date}: {e}")

    if all_available_slots:
        send_discord_alert(all_available_slots)
    else:
        print("❌ No matching slots available in the next 7 days.")

def send_discord_alert(available_data):
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    
    if not webhook_url:
        print("Discord Webhook URL missing. Skipping notification and just printing logs.")
        return

    msg_lines = ["🎾 **Tennis Courts Available!**\n"]
    
    # Format the message nicely for multiple dates and locations
    for target_date, locations in available_data.items():
        day_name = datetime.strptime(target_date, "%Y-%m-%d").strftime("%A")
        msg_lines.append(f"📅 **{day_name}, {target_date}**")
        
        for location, slots in locations.items():
            slug = LOCATIONS[location]
            booking_link = f"https://sportsandleisureroyalparks.bookings.flow.onl/location/{slug}/tennis/{target_date}/by-time"
            
            msg_lines.append(f"📍 {location}: {', '.join(slots)}")
            msg_lines.append(f"🔗 <{booking_link}>")
            
        msg_lines.append("") # Blank line to separate dates

    msg = "\n".join(msg_lines)
    requests.post(webhook_url, json={"content": msg})

if __name__ == "__main__":
    poll_courts()
