import hashlib
import requests
import osint_modules.user_intel as user_intel

DISPOSABLE_DOMAINS = {
    "mailinator.com", "10minutemail.com", "guerrillamail.com", "tempmail.com", "yopmail.com",
    "sharklasers.com", "spam4.me", "grr.la", "dispostable.com", "catch-all.ro"
}

POPULAR_DOMAINS = {
    "gmail.com": "Google Mail",
    "yahoo.com": "Yahoo Mail",
    "hotmail.com": "Microsoft Hotmail",
    "outlook.com": "Microsoft Outlook",
    "aol.com": "AOL Mail",
    "icloud.com": "Apple iCloud",
    "protonmail.com": "Proton Mail (Secure)",
    "pm.me": "Proton Mail (Secure)",
    "tutanota.com": "Tuta (Secure)"
}

def scan_email(email):
    """Scan an email address for intelligence."""
    email = email.lower().strip()
    
    if "@" not in email:
        return {"error": "Invalid email format."}
        
    username, domain = email.split("@", 1)
    
    # 1. Domain Intelligence
    domain_intel = {
        "domain": domain,
        "is_disposable": domain in DISPOSABLE_DOMAINS,
        "provider": POPULAR_DOMAINS.get(domain, "Custom / Private Domain")
    }
    
    # 2. Gravatar Intel
    email_hash = hashlib.md5(email.encode('utf-8')).hexdigest()
    gravatar_url = f"https://www.gravatar.com/avatar/{email_hash}?d=404"
    
    has_gravatar = False
    try:
        res = requests.head(gravatar_url, timeout=3)
        if res.status_code == 200:
            has_gravatar = True
    except:
        pass
        
    # 3. Username Correlation (Run OSINT on the prefix)
    # We do a light/fast version of username intel if possible, or just call the existing one
    username_intel = user_intel.scan_username(username)
    
    return {
        "email": email,
        "username": username,
        "domain_info": domain_intel,
        "gravatar": {
            "has_profile": has_gravatar,
            "url": gravatar_url if has_gravatar else None,
            "hash": email_hash
        },
        "social_profiles": username_intel.get("profiles", [])
    }
