import random
import re
import urllib.request
from scrapling.fetchers import Fetcher, StealthyFetcher
import urllib.parse
import io
import time
import threading
import requests
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import StreamingResponse, RedirectResponse, HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

app = FastAPI(title="Instagram Scraper & Analytics API")

# Enable CORS for frontend interaction
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CACHING SYSTEM ---
# In-memory store: { handle.lower(): (expiry_timestamp, ProfileAnalytics_dict) }
PROFILE_CACHE = {}
CACHE_TTL = 3600  # Cache duration: 1 hour

# --- FREE PROXY ROTATION SYSTEM ---
PROXY_POOL = []
PROXY_LOCK = threading.Lock()
LAST_PROXY_REFRESH = 0
PROXY_REFRESH_INTERVAL = 600  # Refresh proxy list every 10 minutes

def refresh_proxy_pool():
    global PROXY_POOL, LAST_PROXY_REFRESH
    now = time.time()
    if now - LAST_PROXY_REFRESH < PROXY_REFRESH_INTERVAL and len(PROXY_POOL) > 5:
        return

    print("Refreshing free proxy pool...")
    urls = [
        "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt"
    ]
    new_proxies = set()
    for url in urls:
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                for line in r.text.splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        # Ensure it matches ip:port format
                        if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+$', line):
                            new_proxies.add(line)
        except Exception as e:
            print(f"Error fetching proxy list from {url}: {e}")

    with PROXY_LOCK:
        if new_proxies:
            PROXY_POOL = list(new_proxies)
            random.shuffle(PROXY_POOL)
            LAST_PROXY_REFRESH = now
            print(f"Loaded {len(PROXY_POOL)} free HTTP proxies into pool.")
        else:
            print("Failed to fetch new proxies; keeping current pool.")

def get_proxy_candidate() -> Optional[str]:
    refresh_proxy_pool()
    with PROXY_LOCK:
        if PROXY_POOL:
            # Rotate list so we don't always pick the same one
            proxy = PROXY_POOL.pop(0)
            PROXY_POOL.append(proxy)
            return proxy
    return None


@app.get("/", response_class=HTMLResponse)
def read_index():
    return FileResponse("index.html")

@app.get("/index.css")
def read_css():
    return FileResponse("index.css")

@app.get("/main.js")
def read_js():
    return FileResponse("main.js")

class PostDetail(BaseModel):
    id: str
    shortcode: str
    caption: str
    likes: int
    views: Optional[int] = 0
    comments: int
    engagement_rate: float
    sentiment: str
    is_sponsored: bool
    topics: List[str]
    image_url: str
    created_at: str
    media_type: str

class ProfileAnalytics(BaseModel):
    handle: str
    platform: str = "instagram"
    full_name: str
    biography: str
    external_url: Optional[str]
    profile_pic_url: str
    followers: int
    following: int
    posts_count: int
    avg_engagement_rate: float
    fake_follower_percentage: float
    brand_safety_score: float
    sentiment_distribution: Dict[str, float]
    dominant_topics: List[str]
    recent_posts: List[PostDetail]
    estimated_reach: int
    influence_score: float
    likes_to_comments_ratio: float
    images_avg_likes: float
    images_avg_comments: float
    images_er: float
    reels_avg_likes: float
    reels_avg_comments: float
    reels_er: float
    reels_views_to_followers_ratio: float
    reels_avg_views: float = 0.0
    is_simulated: bool
    is_estimated: bool


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (Linux; Android 10; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
]

def get_random_user_agent() -> str:
    return random.choice(USER_AGENTS)

def get_enhanced_headers() -> Dict[str, str]:
    return {
        'User-Agent': get_random_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1'
    }


def parse_stat_val(val_str: str) -> int:
    val_str = val_str.strip().lower().replace(",", "").replace("+", "")
    if not val_str:
        return 0
    multiplier = 1
    if val_str.endswith('b'):
        multiplier = 1_000_000_000
        val_str = val_str[:-1]
    elif val_str.endswith('m'):
        multiplier = 1_000_000
        val_str = val_str[:-1]
    elif val_str.endswith('k'):
        multiplier = 1000
        val_str = val_str[:-1]
    try:
        return int(float(val_str) * multiplier)
    except Exception:
        return 0

def extract_json_by_braces(html: str, start_marker: str) -> Optional[str]:
    idx = html.find(start_marker)
    if idx == -1:
        return None
    start_pos = idx + len(start_marker)
    brace_start = html.find("{", start_pos)
    if brace_start == -1:
        return None
    brace_count = 0
    in_string = False
    escape = False
    for i in range(brace_start, len(html)):
        char = html[i]
        if escape:
            escape = False
            continue
        if char == '\\':
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if not in_string:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    return html[brace_start:i+1]
    return None

def parse_profile_input(input_str: str, query_platform: Optional[str] = None) -> tuple[str, str, str]:
    input_str = input_str.strip()
    parsed_url = urllib.parse.urlparse(input_str)
    
    platform = None
    handle = None
    external_url = None
    
    def clean(username: str) -> str:
        return username.split('?')[0].split('#')[0].strip('/')
        
    if parsed_url.scheme in ('http', 'https') or any(domain in input_str.lower() for domain in ['instagram.com', 'youtube.com', 'twitter.com', 'x.com']):
        url_to_parse = input_str
        if not url_to_parse.startswith('http'):
            url_to_parse = 'https://' + url_to_parse
        try:
            parsed = urllib.parse.urlparse(url_to_parse)
            domain = parsed.netloc.lower()
            path = parsed.path
            
            if 'instagram.com' in domain:
                platform = 'instagram'
                parts = [p for p in path.split('/') if p]
                if parts:
                    handle = clean(parts[0])
                external_url = url_to_parse
            elif 'youtube.com' in domain or 'youtu.be' in domain:
                platform = 'youtube'
                parts = [p for p in path.split('/') if p]
                if parts:
                    if parts[0] in ('user', 'channel', 'c') and len(parts) > 1:
                        handle = clean(parts[1])
                    else:
                        handle = clean(parts[0]).replace('@', '')
                external_url = url_to_parse
            elif 'twitter.com' in domain or 'x.com' in domain:
                platform = 'twitter'
                parts = [p for p in path.split('/') if p]
                if parts:
                    handle = clean(parts[0])
                external_url = url_to_parse
        except Exception as e:
            print(f"Error parsing profile URL: {e}")
            
    if not handle:
        handle = input_str.replace('@', '').strip('/')
        platform = query_platform or 'instagram'
        
        if platform == 'instagram':
            external_url = f"https://www.instagram.com/{handle}/"
        elif platform == 'youtube':
            external_url = f"https://www.youtube.com/@{handle}"
        elif platform == 'twitter':
            external_url = f"https://x.com/{handle}"
            
    handle = handle.replace('@', '').strip()
    return platform or 'instagram', handle, external_url

def extract_platform_metrics_from_html(html: str, clean_handle: str, platform: str) -> Optional[Dict[str, Any]]:
    from bs4 import BeautifulSoup
    import urllib.parse
    import re
    
    soup = BeautifulSoup(html, 'html.parser')
    
    platform_domains = {
        'instagram': ["instagram.com/"],
        'youtube': ["youtube.com/@", "youtube.com/user/", "youtube.com/c/", "youtube.com/channel/"],
        'twitter': ["twitter.com/", "x.com/"]
    }
    
    domains = platform_domains.get(platform, [])
    non_profile_subpaths = ["/sharing", "/sharer", "/intent", "/directory", "/pub/dir", "/help", "/privacy", "/terms", "/about", "/search", "/status", "/hashtag", "/feed"]
    
    for a in soup.find_all('a'):
        href = urllib.parse.unquote(a.get('href', ''))
        matches = False
        for domain in domains:
            if domain in href:
                if not any(sub in href for sub in non_profile_subpaths):
                    matches = True
                    break
                
        if matches:
            parent = a
            for depth in range(5):
                if not parent:
                    break
                text = parent.text.strip()
                
                followers = 0
                following = 0
                posts_count = 0
                
                if platform == 'instagram':
                    followers_match = re.search(r'([\d\.,\+]+[KkMm]?)\s*(?:followers|follower|seguidores|seguidor|abonnés|abonnes|abonne|abonnenten|abonnent|follows|follow|fans|fan)', text, re.IGNORECASE)
                    following_match = re.search(r'([\d\.,\+]+[KkMm]?)\s*(?:following|seguidos|siguiendo|seguido|abonnements|abonnement|abonner|followed)', text, re.IGNORECASE)
                    posts_match = re.search(r'([\d\.,\+]+[KkMm]?)\s*(?:posts|post|publications|publication|beiträge|beitrage|beitrag|publicaciones|publicación|publicacion)', text, re.IGNORECASE)
                    followers = parse_stat_val(followers_match.group(1)) if followers_match else 0
                    following = parse_stat_val(following_match.group(1)) if following_match else 0
                    posts_count = parse_stat_val(posts_match.group(1)) if posts_match else 0
                elif platform == 'youtube':
                    followers_match = re.search(r'([\d\.,\+]+[KkMm]?)\s*(?:subscribers|subscriber|suscriptores|abonnés|subs|sub|abonnés)', text, re.IGNORECASE)
                    posts_match = re.search(r'([\d\.,\+]+[KkMm]?)\s*(?:videos|video|vídeos|videoclips|uploads)', text, re.IGNORECASE)
                    followers = parse_stat_val(followers_match.group(1)) if followers_match else 0
                    posts_count = parse_stat_val(posts_match.group(1)) if posts_match else 0
                elif platform == 'twitter':
                    followers_match = re.search(r'([\d\.,\+]+[KkMm]?)\s*(?:followers|follower|seguidores|seguidor|abonnés)', text, re.IGNORECASE)
                    following_match = re.search(r'([\d\.,\+]+[KkMm]?)\s*(?:following|seguidos|siguiendo|abonnements)', text, re.IGNORECASE)
                    posts_match = re.search(r'([\d\.,\+]+[KkMm]?)\s*(?:posts|tweets|tweets|posts|beiträge)', text, re.IGNORECASE)
                    followers = parse_stat_val(followers_match.group(1)) if followers_match else 0
                    following = parse_stat_val(following_match.group(1)) if following_match else 0
                    posts_count = parse_stat_val(posts_match.group(1)) if posts_match else 0
                    
                if followers > 0 or posts_count > 0:
                    bio = ""
                    parent_result = parent
                    for _ in range(4):
                        if not parent_result:
                            break
                        desc_tag = parent_result.find(class_=re.compile(r'snippet|desc|text|abstract|summary', re.IGNORECASE))
                        if desc_tag:
                            bio = desc_tag.text.strip()
                            break
                        parent_result = parent_result.parent
                    
                    return {
                        "followers": followers,
                        "following": following,
                        "posts_count": posts_count,
                        "biography": bio
                    }
                parent = parent.parent
    return None

def fetch_youtube_oembed(handle: str) -> Optional[Dict[str, str]]:
    import requests
    try:
        url = f"https://www.youtube.com/@{handle}"
        r = requests.get(f"https://www.youtube.com/oembed?url={url}&format=json", timeout=5)
        if r.status_code == 200:
            data = r.json()
            return {
                "full_name": data.get("title", handle.title()),
                "author_name": data.get("author_name", handle),
                "profile_pic_url": data.get("thumbnail_url", "")
            }
    except Exception as e:
        print(f"YouTube oEmbed fetch failed: {e}")
    return None

def scrape_youtube_profile_direct(handle: str) -> Optional[Dict[str, Any]]:
    import concurrent.futures
    from bs4 import BeautifulSoup
    from scrapling.fetchers import Fetcher
    import re
    import json
    
    clean_handle = handle.lower().replace("@", "").strip()
    
    url_home = f"https://www.youtube.com/@{clean_handle}"
    url_videos = f"https://www.youtube.com/@{clean_handle}/videos"
    url_shorts = f"https://www.youtube.com/@{clean_handle}/shorts"
    
    def fetch_url(url):
        try:
            print(f"Fetching YouTube URL: {url}")
            page = Fetcher.get(url, impersonate='chrome')
            return url, page.html_content
        except Exception as e:
            print(f"Failed to fetch YouTube URL {url}: {e}")
            return url, None
            
    try:
        html_home, html_videos, html_shorts = None, None, None
        
        urls = [url_home, url_videos, url_shorts]
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            results = executor.map(fetch_url, urls)
            for url, html in results:
                if url == url_home:
                    html_home = html
                elif url == url_videos:
                    html_videos = html
                elif url == url_shorts:
                    html_shorts = html
                    
        if not html_home:
            print("Home page fetch failed, cannot parse channel profile.")
            return None
            
        soup = BeautifulSoup(html_home, 'html.parser')
        
        # 1. Author Name
        og_title = soup.find("meta", property="og:title")
        full_name = og_title["content"] if og_title else ""
        
        # 2. Bio/Description
        og_desc = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name": "description"})
        biography = og_desc["content"] if og_desc else ""
        
        # 3. Avatar
        og_image = soup.find("meta", property="og:image")
        profile_pic_url = og_image["content"] if og_image else ""
        
        # 4. oEmbed fallback if name/avatar not found
        if not full_name or not profile_pic_url:
            oembed_data = fetch_youtube_oembed(clean_handle)
            if oembed_data:
                if not full_name:
                    full_name = oembed_data.get("full_name")
                if not profile_pic_url:
                    profile_pic_url = oembed_data.get("profile_pic_url")
                    
        if not full_name:
            full_name = clean_handle.title()
            
        followers = 0
        posts_count = 0
        
        # Check metadataParts pattern first
        pattern = r'"metadataParts"\s*:\s*\[\s*\{\s*"text"\s*:\s*\{\s*"content"\s*:\s*"([^"]+)"\s*\}[^}]*\}\s*,\s*\{\s*"text"\s*:\s*\{\s*"content"\s*:\s*"([^"]+)"'
        for m in re.finditer(pattern, html_home):
            val1 = m.group(1)
            val2 = m.group(2)
            if 'subscriber' in val1.lower():
                followers = parse_stat_val(val1.split()[0])
                posts_count = parse_stat_val(val2.split()[0])
                break
                
        # Fallback subscriber regex
        if followers == 0:
            pattern_handle_sub = r'@' + re.escape(clean_handle) + r'[^\w]*•[^\w]*([\d\.,\+]+[KkMm]?)\s*subscribers'
            match = re.search(pattern_handle_sub, html_home, re.IGNORECASE)
            if match:
                followers = parse_stat_val(match.group(1))
            else:
                m_sub = re.search(r'([\d\.,\+]+[KkMm]?)\s*subscribers', html_home, re.IGNORECASE)
                if m_sub:
                    followers = parse_stat_val(m_sub.group(1))
                    
        if posts_count == 0:
            m_vid = re.search(r'([\d\.,\+]+[KkMm]?)\s*(?:videos|video)', html_home, re.IGNORECASE)
            if m_vid:
                posts_count = parse_stat_val(m_vid.group(1))
                
        # --- Parse Recent Videos and Shorts ---
        recent_posts = []
        
        def find_rich_grid(json_data):
            if isinstance(json_data, dict):
                if 'richGridRenderer' in json_data:
                    return json_data['richGridRenderer']
                for k, v in json_data.items():
                    res = find_rich_grid(v)
                    if res:
                        return res
            elif isinstance(json_data, list):
                for item in json_data:
                    res = find_rich_grid(item)
                    if res:
                        return res
            return None
            
        def find_all_keys(json_data, target_key):
            keys_list = []
            if isinstance(json_data, dict):
                if target_key in json_data:
                    keys_list.append(json_data[target_key])
                for k, v in json_data.items():
                    keys_list.extend(find_all_keys(v, target_key))
            elif isinstance(json_data, list):
                for item in json_data:
                    keys_list.extend(find_all_keys(item, target_key))
            return keys_list

        # Parse Longform Videos
        if html_videos:
            try:
                js_v_str = extract_json_by_braces(html_videos, "var ytInitialData =") or extract_json_by_braces(html_videos, 'window["ytInitialData"] =')
                if js_v_str:
                    data_videos = json.loads(js_v_str)
                    grid_videos = find_rich_grid(data_videos)
                    if grid_videos:
                        contents = grid_videos.get("contents", [])
                        for idx, item in enumerate(contents):
                            lockup = item.get('richItemRenderer', {}).get('content', {}).get('lockupViewModel', {})
                            if lockup:
                                content_id = lockup.get("contentId", "")
                                metadata = lockup.get('metadata', {}).get('lockupMetadataViewModel', {})
                                title_val = metadata.get("title", {}).get("content", "")
                                
                                views_val = 0
                                time_val = ""
                                meta_vm = metadata.get("metadata", {}).get("contentMetadataViewModel", {})
                                rows = meta_vm.get("metadataRows", [])
                                if rows:
                                    parts = rows[0].get("metadataParts", [])
                                    if len(parts) > 0:
                                        views_raw = parts[0].get("text", {}).get("content", "")
                                        views_val = parse_stat_val(views_raw.split()[0])
                                    if len(parts) > 1:
                                        time_val = parts[1].get("text", {}).get("content", "")
                                        
                                if content_id and title_val:
                                    recent_posts.append({
                                        "id": f"yt_video_{content_id}",
                                        "shortcode": content_id,
                                        "image_url": f"https://i.ytimg.com/vi/{content_id}/hqdefault.jpg",
                                        "caption": title_val,
                                        "likes": 0,
                                        "views": views_val,
                                        "comments": 0,
                                        "media_type": "video",
                                        "timestamp": time_val,
                                        "created_at": time_val,
                                        "engagement_rate": 0.0,
                                        "is_sponsored": False,
                                        "sentiment": "neutral",
                                        "topics": ["video", "tech"]
                                    })
            except Exception as e:
                print(f"Error parsing YouTube videos JSON: {e}")

        # Parse Shorts — correct field paths from actual shortsLockupViewModel structure:
        # title+views are in accessibilityText, videoId is nested under onTap.innertubeCommand.reelWatchEndpoint.videoId
        if html_shorts:
            try:
                js_s_str = extract_json_by_braces(html_shorts, "var ytInitialData =") or extract_json_by_braces(html_shorts, 'window["ytInitialData"] =')
                if js_s_str:
                    data_shorts = json.loads(js_s_str)
                    grid_shorts = find_rich_grid(data_shorts)
                    if grid_shorts:
                        contents = grid_shorts.get("contents", [])
                        for idx, item in enumerate(contents):
                            shorts_model = item.get('richItemRenderer', {}).get('content', {}).get('shortsLockupViewModel', {})
                            if shorts_model:
                                # Parse title and views from accessibilityText
                                # e.g. "Apple Products That DON'T Exist, 3.1 million views - play Short"
                                accessibility_text = shorts_model.get("accessibilityText", "")
                                title_val = ""
                                views_val = 0
                                if accessibility_text:
                                    # Split on ", " to separate title from view count
                                    import re as _re
                                    view_match = _re.search(r',\s*([\d\.]+\s*(?:million|billion|thousand|[KkMmBb])?)\s*views', accessibility_text, _re.IGNORECASE)
                                    if view_match:
                                        views_raw = view_match.group(1).strip()
                                        # Normalize: "3.1 million" -> "3100000"
                                        views_raw_clean = views_raw.lower().replace(" million", "m").replace(" billion", "b").replace(" thousand", "k")
                                        views_val = parse_stat_val(views_raw_clean)
                                        # Title is everything before the view count match
                                        title_val = accessibility_text[:view_match.start()].strip().rstrip(',')
                                    else:
                                        # Fallback: title is everything before " - play Short"
                                        play_idx = accessibility_text.lower().find(" - play short")
                                        title_val = accessibility_text[:play_idx] if play_idx != -1 else accessibility_text

                                # Get videoId from onTap.innertubeCommand.reelWatchEndpoint.videoId
                                content_id = (
                                    shorts_model
                                    .get("onTap", {})
                                    .get("innertubeCommand", {})
                                    .get("reelWatchEndpoint", {})
                                    .get("videoId", "")
                                )
                                # Fallback: search all keys for videoId
                                if not content_id:
                                    all_ids = find_all_keys(shorts_model, "videoId")
                                    content_id = all_ids[0] if all_ids else ""

                                # Thumbnail: prefer frame0.jpg from reelWatchEndpoint thumbnails
                                thumb_url = f"https://i.ytimg.com/vi/{content_id}/hqdefault.jpg"
                                reel_thumb = (
                                    shorts_model
                                    .get("onTap", {})
                                    .get("innertubeCommand", {})
                                    .get("reelWatchEndpoint", {})
                                    .get("thumbnail", {})
                                    .get("thumbnails", [])
                                )
                                if reel_thumb:
                                    thumb_url = reel_thumb[-1].get("url", thumb_url)

                                if content_id and title_val:
                                    recent_posts.append({
                                        "id": f"yt_short_{content_id}",
                                        "shortcode": content_id,
                                        "image_url": thumb_url,
                                        "caption": title_val,
                                        "likes": 0,
                                        "views": views_val,
                                        "comments": 0,
                                        "media_type": "short",
                                        "timestamp": "",
                                        "created_at": "",
                                        "engagement_rate": 0.0,
                                        "is_sponsored": False,
                                        "sentiment": "neutral",
                                        "topics": ["short"]
                                    })
            except Exception as e:
                print(f"Error parsing YouTube shorts JSON: {e}")

        # Use Playwright to fetch per-video view and comment counts from the rendered DOM.
        # YouTube hides like counts from unauthenticated users (since Nov 2021).
        # Views appear in ytd-video-primary-info-renderer, comments in #comments #count.
        target_posts = recent_posts[5:105]

        if target_posts:
            print(f"Fetching YouTube video details (Playwright) for {len(target_posts)} posts...")
            try:
                from playwright.sync_api import sync_playwright
                with sync_playwright() as pw:
                    browser = pw.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu"])
                    ctx = browser.new_context(
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                        viewport={"width": 1920, "height": 1080}
                    )

                    def scrape_watch_page(post):
                        video_id_p = post["shortcode"]
                        watch_url = f"https://www.youtube.com/watch?v={video_id_p}"
                        try:
                            pg = ctx.new_page()
                            pg.goto(watch_url, wait_until="domcontentloaded", timeout=20000)
                            pg.wait_for_load_state("networkidle", timeout=10000)
                            # Scroll to trigger comment count render
                            pg.evaluate("window.scrollTo(0, 600)")
                            pg.wait_for_timeout(1500)

                            # View count
                            view_text = ""
                            for sel in ["ytd-video-primary-info-renderer .view-count", "span.view-count"]:
                                try:
                                    el = pg.query_selector(sel)
                                    if el:
                                        view_text = el.inner_text().strip()
                                        break
                                except:
                                    pass
                            if view_text:
                                # e.g. "1,785,905,055 views" or "1.8B views"
                                view_num = view_text.replace(" views", "").replace(",", "").strip()
                                post["views"] = parse_stat_val(view_num)

                            # Comment count
                            comment_text = ""
                            for sel in ["#comments #count", "ytd-comments-header-renderer #count"]:
                                try:
                                    el = pg.query_selector(sel)
                                    if el:
                                        comment_text = el.inner_text().strip()
                                        break
                                except:
                                    pass
                            if comment_text:
                                # e.g. "2,442,883 Comments"
                                comment_num = comment_text.lower().replace(" comments", "").replace(",", "").strip()
                                post["comments"] = parse_stat_val(comment_num)

                            pg.close()
                        except Exception as e:
                            print(f"Playwright watch page error for {video_id_p}: {e}")
                            try:
                                pg.close()
                            except:
                                pass
                        return post

                    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                        target_posts = list(executor.map(scrape_watch_page, target_posts))

                    browser.close()
            except Exception as e:
                print(f"Playwright batch scrape failed: {e}")

        recent_posts = target_posts

        return {
            "handle": clean_handle,
            "full_name": full_name,
            "biography": biography,
            "external_url": url_home,
            "profile_pic_url": profile_pic_url,
            "followers": followers,
            "following": 0,
            "posts_count": posts_count or len(recent_posts),
            "recent_posts": recent_posts,
            "is_estimated": False
        }
    except Exception as e:
        print(f"Direct YouTube scrape failed for {clean_handle}: {e}")
        return None


def scrape_twitter_profile_direct(handle: str) -> Optional[Dict[str, Any]]:
    from bs4 import BeautifulSoup
    from scrapling.fetchers import StealthySession
    import re
    import json

    clean_handle = handle.lower().replace("@", "").strip()
    url = f"https://www.sotwe.com/{clean_handle}"
    print(f"Scraping Twitter profile via Sotwe: {url}")
    try:
        html = None
        try:
            with StealthySession(headless=True, solve_cloudflare=True) as session:
                page = session.fetch(url)
                if page.status == 200:
                    html = page.html_content
        except Exception as e:
            print(f"Sotwe fetch failed for {clean_handle}: {e}")

        if not html:
            # Fallback to direct fetch in case cloudflare isn't active
            from scrapling.fetchers import Fetcher
            try:
                page = Fetcher.get(url, impersonate='chrome', timeout=10)
                if page.status == 200:
                    html = page.html_content
            except Exception as e:
                print(f"Fallback Fetcher get failed for Sotwe: {e}")

        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')

        # 1. Full name
        full_name = ""
        h1 = soup.find("h1", class_=re.compile("title", re.I))
        if h1:
            full_name = h1.text.strip()
        if not full_name:
            full_name = clean_handle.title()

        # 2. Bio/Biography
        biography = ""
        bio_div = soup.find("div", class_=re.compile("dynamic-link-content|break-word", re.I))
        if bio_div:
            biography = bio_div.text.strip()

        # 3. Profile picture
        profile_pic_url = ""
        for img in soup.find_all("img"):
            alt = img.get("alt", "")
            if "profile image" in alt.lower() or "avatar" in alt.lower():
                profile_pic_url = img.get("src", "")
                break
        if not profile_pic_url:
            img = soup.find("img", class_="img-content")
            if img:
                profile_pic_url = img.get("src", "")

        # 4. Followers and Following
        followers = 0
        following = 0
        posts_count = 0

        # Look for divs containing stats
        for div in soup.find_all("div"):
            txt = div.text.strip().lower()
            if "following" in txt and ("follower" in txt or "followers" in txt):
                spans = div.find_all("span", class_="font-weight-bold")
                texts = [s.text.strip() for s in spans]
                if len(texts) >= 3:
                    following = parse_stat_val(texts[0])
                    followers = parse_stat_val(texts[1])
                    posts_count = parse_stat_val(texts[2])
                elif len(texts) == 2:
                    following = parse_stat_val(texts[0])
                    followers = parse_stat_val(texts[1])
                break

        # Fallbacks
        if followers == 0:
            for div in soup.find_all("div"):
                txt = div.text.strip()
                if "Follower" in txt:
                    m = re.search(r'([\d\.,\+]+[KkMm]?)\s*Follower', txt, re.I)
                    if m:
                        followers = parse_stat_val(m.group(1))
                if "Following" in txt:
                    m = re.search(r'([\d\.,\+]+[KkMm]?)\s*Following', txt, re.I)
                    if m:
                        following = parse_stat_val(m.group(1))
                if "Post" in txt:
                    m = re.search(r'([\d\.,\+]+[KkMm]?)\s*Post', txt, re.I)
                    if m:
                        posts_count = parse_stat_val(m.group(1))

        # 5. Recent posts
        recent_posts = []
        tweet_cards = soup.find_all(class_=re.compile("tweet-card", re.I))
        for idx, card in enumerate(tweet_cards[:105]):
            text_div = card.find(class_=re.compile("tweet-text", re.I))
            caption = text_div.text.strip() if text_div else ""

            time_div = card.find(class_=re.compile("subtitle|date", re.I))
            timestamp = time_div.text.strip() if time_div else ""

            likes_val = 0
            comments_val = 0
            views_val = 0
            retweets_val = 0

            stats_container = card.find(class_=re.compile("tweet-stats", re.I))
            if stats_container:
                items = stats_container.find_all(class_=re.compile("tweet-stats-item", re.I))
                for item in items:
                    icon = item.find("i") or item.find("svg")
                    if icon:
                        classes = "".join(icon.get("class", [])).lower()
                        val = parse_stat_val(item.text.strip())
                        if "comment" in classes:
                            comments_val = val
                        elif "heart" in classes:
                            likes_val = val
                        elif "retweet" in classes:
                            retweets_val = val
                        elif "chart" in classes or "bar" in classes:
                            views_val = val

            media_img = card.find("img", class_=re.compile("media|tweet-img|img-content", re.I))
            image_url = media_img.get("src", "") if media_img else ""
            if not image_url:
                image_url = "https://images.unsplash.com/photo-1611605698335-8b15d27e03f3?w=500&auto=format&fit=crop&q=60"

            post_data = {
                "id": f"tw_{clean_handle}_{idx}",
                "shortcode": str(idx),
                "image_url": image_url,
                "caption": caption,
                "likes": likes_val,
                "views": views_val,
                "comments": comments_val,
                "media_type": "video" if "video" in caption.lower() else "image",
                "timestamp": timestamp,
                "created_at": timestamp,
                "engagement_rate": 0.0,
                "is_sponsored": False,
                "sentiment": "neutral",
                "topics": ["tech"]
            }
            recent_posts.append(post_data)

        recent_posts = recent_posts[5:105]
        return {
            "handle": clean_handle,
            "full_name": full_name,
            "biography": biography,
            "external_url": f"https://x.com/{clean_handle}",
            "profile_pic_url": profile_pic_url,
            "followers": followers if followers > 0 else 100,
            "following": following,
            "posts_count": posts_count if posts_count > 0 else len(recent_posts),
            "recent_posts": recent_posts,
            "is_estimated": False
        }
    except Exception as e:
        print(f"Sotwe Twitter scrape failed for {clean_handle}: {e}")
        return None



def extract_metrics_from_html(html: str, clean_handle: str) -> Optional[Dict[str, int]]:
    from bs4 import BeautifulSoup
    import urllib.parse
    import re
    
    soup = BeautifulSoup(html, 'html.parser')
    for a in soup.find_all('a'):
        href = urllib.parse.unquote(a.get('href', ''))
        # Try to find a link that points to the user's instagram profile
        if f"instagram.com/{clean_handle}" in href or href.endswith(f"/{clean_handle}/") or href.endswith(f"/{clean_handle}"):
            # Walk up to 5 parent levels to grab the text context containing followers/following metrics
            parent = a
            for depth in range(5):
                if not parent:
                    break
                text = parent.text.strip()
                
                # Broad, case-insensitive, internationalized matchers for followers, following, and posts count
                followers_match = re.search(r'([\d\.,]+[KkMm]?)\s*(?:followers|follower|seguidores|seguidor|abonnés|abonnes|abonne|abonnenten|abonnent|follows|follow|fans|fan)', text, re.IGNORECASE)
                following_match = re.search(r'([\d\.,]+[KkMm]?)\s*(?:following|seguidos|siguiendo|seguido|abonnements|abonnement|abonner|followed)', text, re.IGNORECASE)
                posts_match = re.search(r'([\d\.,]+[KkMm]?)\s*(?:posts|post|publications|publication|beiträge|beitrage|beitrag|publicaciones|publicación|publicacion)', text, re.IGNORECASE)
                
                followers = parse_stat_val(followers_match.group(1)) if followers_match else 0
                following = parse_stat_val(following_match.group(1)) if following_match else 0
                posts_count = parse_stat_val(posts_match.group(1)) if posts_match else 0
                
                if followers > 0:
                    return {
                        "followers": followers,
                        "following": following,
                        "posts_count": posts_count
                    }
                parent = parent.parent
    return None

def scrape_followers_from_search(handle: str) -> Optional[Dict[str, int]]:
    import urllib.parse
    from scrapling.fetchers import Fetcher
    import concurrent.futures
    
    clean_handle = handle.lower().replace("@", "").strip()
    query = f"{clean_handle} instagram"
    
    def fetch_yahoo():
        url_yahoo = f"https://search.yahoo.com/search?q={urllib.parse.quote(query)}"
        try:
            page = Fetcher.get(url_yahoo, impersonate='chrome')
            html = str(page.css("body").get())
            stats = extract_metrics_from_html(html, clean_handle)
            if stats:
                return stats
        except Exception as e:
            print(f"Yahoo search fallback failed for {clean_handle}: {e}")
        return None

    def fetch_ddg():
        url_ddg = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        try:
            page = Fetcher.get(url_ddg, impersonate='chrome')
            html = str(page.css("body").get())
            stats = extract_metrics_from_html(html, clean_handle)
            if stats:
                return stats
        except Exception as e:
            print(f"DuckDuckGo search fallback failed for {clean_handle}: {e}")
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(fetch_yahoo), executor.submit(fetch_ddg)]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                return res

    return None

def scrape_instagram_profile_live(handle: str) -> Optional[Dict[str, Any]]:
    import requests
    import re
    from bs4 import BeautifulSoup
    from scrapling.fetchers import Fetcher
    
    clean_handle = handle.lower().replace("@", "").strip()
    
    response_json = None
    
    # 1. Try direct fetch first (no proxy)
    headers = {
        'User-Agent': get_random_user_agent(),
        'x-ig-app-id': '936619743392459',
    }
    try:
        print(f"Fetching posts from Instagram API (direct) for {clean_handle}...")
        r = requests.get(f'https://www.instagram.com/api/v1/users/web_profile_info/?username={clean_handle}', headers=headers, timeout=6)
        if r.status_code == 200:
            response_json = r.json()
        else:
            print(f"Direct Instagram API fetch returned status {r.status_code}")
    except Exception as e:
        print(f"Direct Instagram API fetch failed: {e}")

    # 2. Try proxy rotation fallback if direct failed
    if not response_json:
        for attempt in range(4):
            proxy = get_proxy_candidate()
            if not proxy:
                print("No proxy candidates available in pool.")
                break
            print(f"Attempting Instagram API via proxy: {proxy} (attempt {attempt+1}/4) for {clean_handle}...")
            proxies = {"http": f"http://{proxy}", "https": f"http://{proxy}"}
            try:
                headers = {
                    'User-Agent': get_random_user_agent(),
                    'x-ig-app-id': '936619743392459',
                }
                r = requests.get(
                    f'https://www.instagram.com/api/v1/users/web_profile_info/?username={clean_handle}',
                    headers=headers,
                    proxies=proxies,
                    timeout=5
                )
                if r.status_code == 200:
                    response_json = r.json()
                    print(f"Successfully fetched via proxy {proxy}!")
                    break
                else:
                    print(f"Proxy {proxy} returned status code {r.status_code}")
            except Exception as e:
                print(f"Proxy {proxy} failed or timed out: {e}")

    if response_json:
        try:
            user = response_json.get('data', {}).get('user')
            if user:
                followers_count = user.get('edge_followed_by', {}).get('count', 0)
                following = user.get('edge_follow', {}).get('count', 0)
                posts_count = user.get('edge_owner_to_timeline_media', {}).get('count', 0)
                full_name = user.get('full_name') or clean_handle.title()
                bio = user.get('biography', '')
                profile_pic_url = make_proxy_url(user.get('profile_pic_url_hd') or user.get('profile_pic_url'))
                external_url = user.get('external_url')
                
                recent_posts = []
                edges = user.get('edge_owner_to_timeline_media', {}).get('edges', [])
                for edge in edges:
                    node = edge.get('node', {})
                    shortcode = node.get('shortcode', '')
                    likes = node.get('edge_liked_by', {}).get('count', 0)
                    comments = node.get('edge_media_to_comment', {}).get('count', 0)
                    
                    caption_edges = node.get('edge_media_to_caption', {}).get('edges', [])
                    caption_text = caption_edges[0]['node']['text'] if caption_edges else ""
                    caption_lower = caption_text.lower()
                    
                    is_sponsored = any(kw in caption_lower for kw in ['#ad', '#sponsored', 'paid partnership', 'sponsored by', 'partnership'])
                    
                    sentiment = "neutral"
                    topics = []
                    
                    views = node.get('video_play_count') or node.get('video_view_count') or node.get('play_count') or 0
                    post_er = round(((likes + comments) / max(followers_count, 1)) * 100.0, 2)
                    
                    typename = node.get('__typename', '')
                    media_type = "video" if typename == 'GraphVideo' else "image"
                    timestamp = str(node.get('taken_at_timestamp', ''))
                    
                    final_img_url = make_proxy_url(node.get('display_url', ''))
                    
                    post_data = {
                        "id": node.get('id', ''),
                        "shortcode": shortcode,
                        "image_url": final_img_url,
                        "caption": caption_text, 
                        "likes": likes,
                        "views": views,
                        "comments": comments,
                        "media_type": media_type,
                        "timestamp": timestamp,
                        "created_at": timestamp,
                        "engagement_rate": post_er,
                        "is_sponsored": is_sponsored,
                        "sentiment": sentiment,
                        "topics": topics
                    }
                    recent_posts.append(post_data)
                    
                recent_posts = recent_posts[5:105]
                return {
                    "handle": clean_handle,
                    "full_name": full_name,
                    "biography": bio,
                    "external_url": external_url or f"https://www.instagram.com/{clean_handle}/",
                    "profile_pic_url": profile_pic_url,
                    "followers": followers_count,
                    "following": following,
                    "posts_count": posts_count,
                    "recent_posts": recent_posts,
                    "is_estimated": False
                }
        except Exception as e:
            print(f"Error parsing Instagram API JSON for {clean_handle}: {e}")

    # Fallback to pixwox
    from scrapling.fetchers import StealthySession
    
    def fetch_pixwox():
        pixwox_url = f"https://www.pixwox.com/profile/{clean_handle}/"
        print(f"Fetching posts from {pixwox_url}...")
        try:
            with StealthySession(headless=True, solve_cloudflare=True) as session:
                page = session.fetch(pixwox_url, google_search=False)
                return str(page.css("body").get())
        except Exception as e:
            print(f"Failed to fetch posts from pixwox for {clean_handle}: {e}")
            return None

    pixwox_html = fetch_pixwox()
            
    followers_count = 0
    posts_count = 0
    following = 0
    full_name = clean_handle.title()
    bio = ""
    profile_pic_url = f"https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80"
    recent_posts = []

    if pixwox_html:
        try:
            soup2 = BeautifulSoup(pixwox_html, 'html.parser')
            
            # Extract Profile Info from pixwox
            name_tag = soup2.find('h1', class_='fullname')
            if name_tag: full_name = name_tag.text.strip()
            
            # The bio is usually in div.sum inside div.info
            info_div = soup2.find('div', class_='info')
            if info_div:
                bio_tag = info_div.find('div', class_='sum')
                if bio_tag: bio = bio_tag.text.strip()
            
            avatar_tag = soup2.select_one('.ava .pic img')
            if avatar_tag and avatar_tag.get('src'):
                profile_pic_url = make_proxy_url(avatar_tag.get('src'))
                
            followers_div = soup2.find('div', class_='item_followers')
            if followers_div:
                num_tag = followers_div.find('div', class_='num')
                if num_tag and 'title' in num_tag.attrs:
                    followers_count = parse_stat_val(num_tag['title'])
                elif num_tag:
                    followers_count = parse_stat_val(num_tag.text)
            
            posts_div = soup2.find('div', class_='item_posts')
            if posts_div:
                num_tag = posts_div.find('div', class_='num')
                if num_tag and 'title' in num_tag.attrs:
                    posts_count = parse_stat_val(num_tag['title'])
                elif num_tag:
                    posts_count = parse_stat_val(num_tag.text)
                    
            following_div = soup2.find('div', class_='item_following')
            if following_div:
                num_tag = following_div.find('div', class_='num')
                if num_tag and 'title' in num_tag.attrs:
                    following = parse_stat_val(num_tag['title'])
                elif num_tag:
                    following = parse_stat_val(num_tag.text)
                        
            items = soup2.find_all('div', class_='item')
            for idx, item in enumerate(items):
                like_div = item.find("span", class_="count_item_like") or item.find("div", class_="count_item_like")
                comment_div = item.find("span", class_="count_item_comment") or item.find("div", class_="count_item_comment")
                
                # If there are no like/comment divs, this might be a header/nav item, so skip
                if not like_div and not comment_div:
                    continue
                    
                likes = parse_stat_val(like_div.text.strip()) if like_div else 0
                comments = parse_stat_val(comment_div.text.strip()) if comment_div else 0
                
                img_tag = item.find("img")
                img_url = img_tag.get("src", "") if img_tag else ""
                if img_url.startswith("data:image") or not img_url:
                    img_url = img_tag.get("data-src", "") if img_tag else ""
                    
                final_img_url = make_proxy_url(img_url)
                    
                media_type = "image"
                if item.find(class_=lambda c: c and "video" in str(c).lower() or "play" in str(c).lower()):
                    media_type = "video"
                    
                time_div = item.find("div", class_="time")
                timestamp = time_div.text.strip() if time_div else ""
                
                a_tag = item.find("a")
                shortcode = ""
                if a_tag and "href" in a_tag.attrs:
                    parts = [p for p in a_tag["href"].split("/") if p]
                    if parts:
                        shortcode = parts[-1]
                
                caption_div = item.find("div", class_="sum")
                caption_text = caption_div.text.strip() if caption_div else ""
                caption_lower = caption_text.lower()
                
                is_sponsored = any(kw in caption_lower for kw in ['#ad', '#sponsored', 'paid partnership', 'sponsored by', 'partnership'])
                
                sentiment = "neutral"
                topics = []
                
                views = 0
                views_div = item.find("span", class_="count_item_play") or item.find("div", class_="count_item_play")
                if views_div:
                    views = parse_stat_val(views_div.text.strip())
                
                post_er = round(((likes + comments) / max(followers_count, 1)) * 100.0, 2)
                    
                post_data = {
                    "id": "",
                    "shortcode": shortcode,
                    "image_url": final_img_url,
                    "caption": caption_text, 
                    "likes": likes,
                    "views": views,
                    "comments": comments,
                    "media_type": media_type,
                    "timestamp": timestamp,
                    "created_at": timestamp,
                    "engagement_rate": post_er,
                    "is_sponsored": is_sponsored,
                    "sentiment": sentiment,
                    "topics": topics
                }
                recent_posts.append(post_data)
            recent_posts = recent_posts[5:105]
        except Exception as e:
            print(f"Error parsing pixwox for {handle}: {e}")

    if followers_count <= 0:
        search_stats = scrape_followers_from_search(clean_handle)
        if search_stats:
            followers_count = search_stats.get("followers", 0)
            following = search_stats.get("following", 0)
            posts_count = search_stats.get("posts_count", 0)

    return {
        "handle": clean_handle,
        "full_name": full_name,
        "biography": bio,
        "external_url": f"https://www.instagram.com/{clean_handle}/",
        "profile_pic_url": profile_pic_url,
        "followers": followers_count,
        "following": following,
        "posts_count": posts_count,
        "recent_posts": recent_posts,
        "is_estimated": False
    }

def make_proxy_url(url: str) -> str:
    if not url:
        return ""
    if "imginn.com" in url or "cdninstagram.com" in url or "fbcdn.net" in url or "instagram" in url:
        import urllib.parse
        return f"http://localhost:8000/api/proxy-image?url={urllib.parse.quote(url)}"
    return url

@app.get("/api/proxy-image")
def proxy_image(url: str):
    if not url:
        raise HTTPException(status_code=400, detail="Missing url parameter")
    decoded_url = urllib.parse.unquote(url)
    if not decoded_url.startswith("http"):
        if decoded_url.startswith("//"):
            decoded_url = "https:" + decoded_url
        elif decoded_url.startswith("/"):
            decoded_url = "https://imginn.com" + decoded_url
        else:
            raise HTTPException(status_code=400, detail="Invalid URL scheme")
    try:
        req = urllib.request.Request(
            decoded_url,
            headers={'User-Agent': get_random_user_agent()}
        )
        response = urllib.request.urlopen(req, timeout=10)
        content_type = response.headers.get('Content-Type', 'image/jpeg')
        return StreamingResponse(io.BytesIO(response.read()), media_type=content_type)
    except Exception as e:
        print(f"Proxy image failed for URL {decoded_url}: {e}")
        return RedirectResponse(url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80")

@app.get("/api/analyze/{handle:path}", response_model=ProfileAnalytics)
def analyze_profile(handle: str, platform: Optional[str] = None):
    resolved_platform, clean_handle, external_url = parse_profile_input(handle, platform)
    
    if not clean_handle:
        raise HTTPException(status_code=400, detail="Invalid username or profile link")
    
    cache_key = f"{resolved_platform}:{clean_handle}"
    
    # Check Cache
    now = time.time()
    if cache_key in PROFILE_CACHE:
        expiry, cached_result = PROFILE_CACHE[cache_key]
        if now < expiry:
            print(f"Cache Hit for {cache_key}. Returning cached result.")
            return cached_result
        else:
            print(f"Cache expired for {cache_key}. Re-fetching.")
            PROFILE_CACHE.pop(cache_key, None)

    # 1. Scraping / Fetching logic based on platform
    scraped = None
    if resolved_platform == 'instagram':
        scraped = scrape_instagram_profile_live(clean_handle)
    elif resolved_platform == 'youtube':
        scraped = scrape_youtube_profile_direct(clean_handle)
    elif resolved_platform == 'twitter':
        scraped = scrape_twitter_profile_direct(clean_handle)

    if scraped:
        posts = []
        total_er = 0.0
        
        for p in scraped["recent_posts"]:
            if resolved_platform == 'youtube':
                # Use views as the engagement metric for YouTube (likes are hidden)
                er = round((p.get("views", 0) / max(scraped["followers"], 1)) * 100.0, 2)
            else:
                er = round(((p["likes"] + p["comments"]) / max(scraped["followers"], 1)) * 100.0, 2)
            post_obj = PostDetail(
                id=p["id"],
                shortcode=p["shortcode"],
                caption=p["caption"],
                likes=p["likes"],
                views=p.get("views", 0),
                comments=p["comments"],
                engagement_rate=er,
                sentiment=p["sentiment"],
                is_sponsored=p["is_sponsored"],
                topics=p.get("topics", []),
                image_url=p["image_url"],
                created_at=p["created_at"],
                media_type=p["media_type"]
            )
            posts.append(post_obj)
            total_er += er
        avg_er = round(total_er / len(posts), 2) if len(posts) > 0 else 0.0
        fake_follower_percentage = 0.0
        sentiment_distribution = {"positive": 0.0, "neutral": 0.0, "negative": 0.0}
        brand_safety_score = 0.0
        dominant_topics = []
        estimated_reach = 0
        influence_score = 0.0
            
        # Separate Image/Text vs Video stats
        if resolved_platform == 'youtube':
            images_posts = [p for p in scraped["recent_posts"] if p["media_type"] == "video"]
            reels_posts = [p for p in scraped["recent_posts"] if p["media_type"] == "short"]
        else:
            images_posts = [p for p in scraped["recent_posts"] if p["media_type"] in ("image", "text")]
            reels_posts = [p for p in scraped["recent_posts"] if p["media_type"] in ("video", "short")]
            
        images_likes = [p["likes"] for p in images_posts]
        images_comments = [p["comments"] for p in images_posts]
        images_views = [p.get("views", 0) for p in images_posts]
        reels_likes = [p["likes"] for p in reels_posts]
        reels_comments = [p["comments"] for p in reels_posts]
        reels_views_list = [p.get("views", 0) for p in reels_posts]

        if resolved_platform == 'youtube':
            # For YouTube: use views as primary engagement metric (likes are hidden by YouTube)
            # Avg. Likes card will show avg views, Avg. Comments will show avg comments
            img_avg_views = round(sum(v for v in images_views if v > 0) / max(len([v for v in images_views if v > 0]), 1), 1)
            img_avg_comments = round(sum(images_comments) / max(len(images_comments), 1), 1)
            img_avg_likes = img_avg_views  # Show views in "Avg. Likes" field for videos
            img_er = round((img_avg_views / max(scraped["followers"], 1)) * 100.0, 2) if scraped["followers"] > 0 else 0.0

            reels_avg_views = round(sum(v for v in reels_views_list if v > 0) / max(len([v for v in reels_views_list if v > 0]), 1), 1)
            reels_avg_comments_val = round(sum(reels_comments) / max(len(reels_comments), 1), 1)
            reels_avg_likes = reels_avg_views  # Show views in "Avg. Likes" field for shorts
            reels_avg_comments = reels_avg_comments_val
            reels_er = round((reels_avg_views / max(scraped["followers"], 1)) * 100.0, 2) if scraped["followers"] > 0 else 0.0

            all_views = [p.get("views", 0) for p in scraped["recent_posts"] if p.get("views", 0) > 0]
            overall_avg_views = sum(all_views) / max(len(all_views), 1) if all_views else 0.0
            reels_views_to_followers_ratio = round((overall_avg_views / max(scraped["followers"], 1)) * 100.0, 2)
        elif resolved_platform == 'instagram':
            img_avg_likes = round(sum(images_likes) / len(images_likes), 1) if images_likes else 0.0
            img_avg_comments = round(sum(images_comments) / len(images_comments), 1) if images_comments else 0.0
            img_er = round(((img_avg_likes + img_avg_comments) / scraped["followers"]) * 100.0, 2) if scraped["followers"] > 0 else 0.0

            reels_avg_likes = round(sum(reels_likes) / len(reels_likes), 1) if reels_likes else 0.0
            reels_avg_comments = round(sum(reels_comments) / len(reels_comments), 1) if reels_comments else 0.0
            reels_er = round(((reels_avg_likes + reels_avg_comments) / scraped["followers"]) * 100.0, 2) if scraped["followers"] > 0 else 0.0

            reels_avg_views = 0.0
            reels_views_to_followers_ratio = 0.0
        else: # twitter
            img_avg_likes = round(sum(images_likes) / len(images_likes), 1) if images_likes else 0.0
            img_avg_comments = round(sum(images_comments) / len(images_comments), 1) if images_comments else 0.0
            img_er = round(((img_avg_likes + img_avg_comments) / scraped["followers"]) * 100.0, 2) if scraped["followers"] > 0 else 0.0

            reels_avg_likes = round(sum(reels_likes) / len(reels_likes), 1) if reels_likes else 0.0
            reels_avg_comments = round(sum(reels_comments) / len(reels_comments), 1) if reels_comments else 0.0
            reels_er = round(((reels_avg_likes + reels_avg_comments) / scraped["followers"]) * 100.0, 2) if scraped["followers"] > 0 else 0.0

            reels_views = [p.get("views", 0) for p in reels_posts if p.get("views", 0) > 0]
            reels_avg_views = sum(reels_views) / len(reels_views) if reels_views else 0.0
            reels_views_to_followers_ratio = round((reels_avg_views / max(scraped["followers"], 1)) * 100.0, 2) if scraped["followers"] > 0 else 0.0

        total_likes = sum(p["likes"] for p in scraped["recent_posts"])
        total_comments = sum(p["comments"] for p in scraped["recent_posts"])
        likes_to_comments_ratio = round(total_likes / max(total_comments, 1), 2)
                    
        result = ProfileAnalytics(
            handle=scraped["handle"],
            platform=resolved_platform,
            full_name=scraped["full_name"],
            biography=scraped["biography"],
            external_url=scraped["external_url"],
            profile_pic_url=scraped["profile_pic_url"],
            followers=scraped["followers"],
            following=scraped["following"],
            posts_count=scraped["posts_count"],
            avg_engagement_rate=avg_er,
            fake_follower_percentage=fake_follower_percentage,
            brand_safety_score=brand_safety_score,
            sentiment_distribution=sentiment_distribution,
            dominant_topics=dominant_topics,
            recent_posts=posts,
            estimated_reach=estimated_reach,
            influence_score=influence_score,
            likes_to_comments_ratio=likes_to_comments_ratio,
            images_avg_likes=img_avg_likes,
            images_avg_comments=img_avg_comments,
            images_er=img_er,
            reels_avg_likes=reels_avg_likes,
            reels_avg_comments=reels_avg_comments,
            reels_er=reels_er,
            reels_views_to_followers_ratio=reels_views_to_followers_ratio,
            reels_avg_views=reels_avg_views,
            is_simulated=False,
            is_estimated=scraped.get("is_estimated", False)
        )
        
        # Cache successful scrape
        if scraped["followers"] > 0:
            PROFILE_CACHE[cache_key] = (time.time() + CACHE_TTL, result)
        else:
            PROFILE_CACHE[cache_key] = (time.time() + 10, result)
            
        return result
    
    # 2. Fallback to empty metrics if scraper fails completely
    fallback_result = ProfileAnalytics(
        handle=clean_handle,
        platform=resolved_platform,
        full_name="N/A",
        biography=f"Unable to fetch real-time data from {resolved_platform.title()}.",
        external_url=None,
        profile_pic_url="",
        followers=0,
        following=0,
        posts_count=0,
        avg_engagement_rate=0.0,
        fake_follower_percentage=0.0,
        brand_safety_score=0.0,
        sentiment_distribution={"positive": 0.0, "neutral": 0.0, "negative": 0.0},
        dominant_topics=[],
        recent_posts=[],
        estimated_reach=0,
        influence_score=0.0,
        likes_to_comments_ratio=0.0,
        images_avg_likes=0.0,
        images_avg_comments=0.0,
        images_er=0.0,
        reels_avg_likes=0.0,
        reels_avg_comments=0.0,
        reels_er=0.0,
        reels_views_to_followers_ratio=0.0,
        reels_avg_views=0.0,
        is_simulated=False,
        is_estimated=False
    )
    PROFILE_CACHE[cache_key] = (time.time() + 10, fallback_result)
    return fallback_result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
