import exifread
import io

def safe_div(num, den):
    if den == 0: return 0
    return num / den

def get_decimal_from_dms(dms, ref):
    try:
        degrees = safe_div(dms[0].num, dms[0].den)
        minutes = safe_div(dms[1].num, dms[1].den) / 60.0
        seconds = safe_div(dms[2].num, dms[2].den) / 3600.0
        
        val = degrees + minutes + seconds
        if ref in ['S', 'W']:
            val = -val
            
        return round(val, 6)
    except Exception:
        return None

def extract_exif(file_bytes):
    try:
        f = io.BytesIO(file_bytes)
        tags = exifread.process_file(f, details=False)
        
        if not tags:
            return {"error": "No EXIF metadata found in this image. (It may have been stripped or wasn't taken with a camera)."}
            
        data = {
            "Make": str(tags.get("Image Make", "Unknown")),
            "Model": str(tags.get("Image Model", "Unknown")),
            "Software": str(tags.get("Image Software", "Unknown")),
            "DateTime": str(tags.get("Image DateTime", "Unknown")),
            "OriginalTime": str(tags.get("EXIF DateTimeOriginal", "Unknown")),
        }
        
        # Clean up unknowns
        data = {k: v for k, v in data.items() if v != "Unknown"}
        if not data and not tags.get("GPS GPSLatitude"):
            return {"error": "Minimal metadata found. No useful fingerprint or location data."}
            
        gps_latitude = tags.get("GPS GPSLatitude")
        gps_latitude_ref = tags.get("GPS GPSLatitudeRef")
        gps_longitude = tags.get("GPS GPSLongitude")
        gps_longitude_ref = tags.get("GPS GPSLongitudeRef")
        
        if gps_latitude and gps_latitude_ref and gps_longitude and gps_longitude_ref:
            lat = get_decimal_from_dms(gps_latitude.values, str(gps_latitude_ref.values))
            lon = get_decimal_from_dms(gps_longitude.values, str(gps_longitude_ref.values))
            if lat is not None and lon is not None:
                data["GPS"] = {
                    "Latitude": lat,
                    "Longitude": lon,
                    "MapLink": f"https://www.google.com/maps?q={lat},{lon}"
                }
            
        return data
        
    except Exception as e:
        return {"error": f"Failed to parse image EXIF: {str(e)}"}
