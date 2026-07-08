import urllib.request
import re

try:
    req = urllib.request.Request('https://shuttletv.su/watch/124364?s=4&e=8', headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        html = response.read().decode('utf-8')
        print(f'HTML Length: {len(html)}')
        if '<video' in html: print('Found <video> tag')
        if '<iframe' in html: print('Found <iframe> tag')
        
        m3u8 = re.findall(r'http[s]?://[^\s\"\'<>]*?\.m3u8', html)
        if m3u8: print('Found m3u8:', m3u8[0])
        
        mp4 = re.findall(r'http[s]?://[^\s\"\'<>]*?\.mp4', html)
        if mp4: print('Found mp4:', mp4[0])
except Exception as e:
    print(e)
