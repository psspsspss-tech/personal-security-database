import requests
import concurrent.futures

def check_platform(url, platform_name):
    try:
        # User-Agent is critical because many platforms block default requests
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        res = requests.get(url, headers=headers, timeout=5, allow_redirects=False)
        # Some return 200 but have "Not Found" in title, we do basic 200 check
        if res.status_code == 200:
            return {"platform": platform_name, "url": url, "found": True}
        return {"platform": platform_name, "url": url, "found": False}
    except:
        return {"platform": platform_name, "url": url, "found": False}

def scan_username(username):
    """
    Checks for the existence of a username across multiple platforms.
    """
    platforms = [
        ("GitHub", f"https://github.com/{username}"),
        ("Reddit", f"https://www.reddit.com/user/{username}/about.json"), # API endpoint is more reliable
        ("Twitter", f"https://nitter.net/{username}"), # Nitter avoids Twitter login block
        ("Steam", f"https://steamcommunity.com/id/{username}"),
        ("Pinterest", f"https://www.pinterest.com/{username}/"),
        ("Spotify", f"https://open.spotify.com/user/{username}"),
        ("Vimeo", f"https://vimeo.com/{username}"),
        ("Twitch", f"https://www.twitch.tv/{username}")
    ]
    
    results = []
    
    # Run requests concurrently for speed
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_url = {executor.submit(check_platform, url, name): (name, url) for name, url in platforms}
        for future in concurrent.futures.as_completed(future_to_url):
            try:
                data = future.result()
                results.append(data)
            except Exception as e:
                pass

    return {
        "username": username,
        "profiles": results
    }
