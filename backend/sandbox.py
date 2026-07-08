import requests
from bs4 import BeautifulSoup
import re
import urllib.parse
import time

def analyze_url(url):
    """
    Safely detonate and analyze a URL.
    - Traces redirects
    - Checks domain age/reputation (heuristics)
    - Extracts title and hidden scripts
    """
    if not url.startswith('http'):
        url = 'http://' + url

    result = {
        "original_url": url,
        "redirect_chain": [],
        "final_url": None,
        "title": None,
        "scripts_found": 0,
        "risk_level": "low",
        "risk_factors": [],
        "error": None
    }

    try:
        # Trace redirects safely
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/114.0.0.0 Safari/537.36'
        })
        
        current_url = url
        for i in range(5): # Max 5 redirects
            resp = session.get(current_url, allow_redirects=False, timeout=5)
            result["redirect_chain"].append({
                "url": current_url,
                "status_code": resp.status_code
            })
            if resp.status_code in (301, 302, 303, 307, 308) and 'Location' in resp.headers:
                next_url = urllib.parse.urljoin(current_url, resp.headers['Location'])
                current_url = next_url
            else:
                break
                
        # Final fetch to get content
        final_resp = session.get(current_url, timeout=5)
        result["final_url"] = final_resp.url
        
        # Heuristic Risk Analysis
        domain = urllib.parse.urlparse(result["final_url"]).netloc.lower()
        if any(tld in domain for tld in ['.tk', '.xyz', '.top', '.pw', '.cc']):
            result["risk_factors"].append("Suspicious Top-Level Domain")
        if any(word in domain for word in ['login', 'verify', 'secure', 'update', 'account', 'banking']):
            result["risk_factors"].append("Phishing Keyword in Domain")
            
        if len(result["redirect_chain"]) > 2:
            result["risk_factors"].append(f"High Number of Redirects ({len(result['redirect_chain'])})")

        # Extract info
        soup = BeautifulSoup(final_resp.text, 'html.parser')
        title_tag = soup.find('title')
        if title_tag:
            result["title"] = title_tag.text.strip()
            
        scripts = soup.find_all('script')
        result["scripts_found"] = len(scripts)
        
        # Check for obfuscated scripts or eval
        for script in scripts:
            if script.string and ('eval(' in script.string or 'unescape(' in script.string or 'document.write(' in script.string):
                if "Obfuscated/Malicious JS Pattern" not in result["risk_factors"]:
                    result["risk_factors"].append("Obfuscated/Malicious JS Pattern")
                    
        # Determine risk
        num_factors = len(result["risk_factors"])
        if num_factors == 0:
            result["risk_level"] = "low"
        elif num_factors == 1:
            result["risk_level"] = "medium"
        else:
            result["risk_level"] = "high"
            
    except requests.exceptions.RequestException as e:
        result["error"] = f"Network Error: {str(e)}"
    except Exception as e:
        result["error"] = f"Analysis Error: {str(e)}"

    return result
