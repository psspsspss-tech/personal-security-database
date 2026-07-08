import phonenumbers
from phonenumbers import geocoder, carrier, timezone
import requests
import urllib.parse

def scan_phone(phone_number):
    try:
        # Auto-prepend '+' if it's purely digits to prevent region error
        if not phone_number.startswith('+'):
            phone_number = '+' + phone_number
            
        parsed = phonenumbers.parse(phone_number, None)
        
        if not phonenumbers.is_valid_number(parsed):
            return {"error": "Invalid phone number. Please include the country code (e.g. +1 or +44)."}
            
        # Get info
        location = geocoder.description_for_number(parsed, "en")
        carrier_name = carrier.name_for_number(parsed, "en")
        time_zones = timezone.time_zones_for_number(parsed)
        
        lat, lon = "Unknown", "Unknown"
        if location and location != "Unknown":
            try:
                headers = {'User-Agent': 'SecurityCommandCenterOSINT/1.0'}
                geo_url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(location)}&format=json&limit=1"
                geo_res = requests.get(geo_url, headers=headers, timeout=5)
                geo_data = geo_res.json()
                if geo_data:
                    lat = geo_data[0].get("lat", "Unknown")
                    lon = geo_data[0].get("lon", "Unknown")
            except Exception as e:
                print("Geocoding failed for phone location:", e)
                
        coordinates = "Unknown"
        if lat != "Unknown" and lon != "Unknown":
            coordinates = f"{lat}, {lon}"
            
        return {
            "number": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
            "country_code": parsed.country_code,
            "national_number": parsed.national_number,
            "location": location if location else "Unknown",
            "coordinates": coordinates,
            "carrier": carrier_name if carrier_name else "Unknown",
            "timezones": list(time_zones)
        }
    except Exception as e:
        error_msg = str(e)
        if "Missing or invalid default region" in error_msg:
            return {"error": "Invalid format. Please include the country code (e.g., +1)."}
        return {"error": error_msg}
