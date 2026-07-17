import requests

def scan_ip(ip_address):
    """
    Geolocates and gets intelligence on an IP address using ip-api.com
    """
    try:
        url = f"http://ip-api.com/json/{ip_address}?fields=status,message,country,regionName,city,zip,lat,lon,timezone,isp,org,as,query"
        response = requests.get(url, timeout=5)
        data = response.json()
        
        if data.get('status') == 'fail':
            return {"error": data.get('message', 'Failed to retrieve IP data')}
            
        return {
            "ip": data.get("query"),
            "location": f"{data.get('city')}, {data.get('regionName')}, {data.get('country')}",
            "coordinates": f"{data.get('lat')}, {data.get('lon')}",
            "isp": data.get("isp"),
            "organization": data.get("org"),
            "timezone": data.get("timezone"),
            "asn": data.get("as")
        }
    except Exception as e:
        return {"error": str(e)}
