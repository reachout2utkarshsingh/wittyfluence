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
    val_str = val_str.strip().lower().replace(",", "")
    if not val_str:
        return 0
    multiplier = 1
    if val_str.endswith('m'):
        multiplier = 1000000
        val_str = val_str[:-1]
    elif val_str.endswith('k'):
        multiplier = 1000
        val_str = val_str[:-1]
    try:
        return int(float(val_str) * multiplier)
    except Exception:
        return 0

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
                    
                    positive_words = ['great', 'awesome', 'amazing', 'love', 'beautiful', 'excellent', 'fantastic', 'good', 'best', 'happy']
                    negative_words = ['bad', 'terrible', 'awful', 'hate', 'worst', 'sad', 'poor', 'disappointing', 'fake', 'scam']
                    pos_score = sum(1 for word in positive_words if word in caption_lower)
                    neg_score = sum(1 for word in negative_words if word in caption_lower)
                    sentiment = "positive" if pos_score > neg_score else "negative" if neg_score > pos_score else "neutral"
                    
                    topics = re.findall(r'#(\w+)', caption_lower)
                    topics = list(dict.fromkeys(topics))[:3]
                    
                    views = node.get('video_view_count', 0)
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
                
                positive_words = ['great', 'awesome', 'amazing', 'love', 'beautiful', 'excellent', 'fantastic', 'good', 'best', 'happy']
                negative_words = ['bad', 'terrible', 'awful', 'hate', 'worst', 'sad', 'poor', 'disappointing', 'fake', 'scam']
                pos_score = sum(1 for word in positive_words if word in caption_lower)
                neg_score = sum(1 for word in negative_words if word in caption_lower)
                sentiment = "positive" if pos_score > neg_score else "negative" if neg_score > pos_score else "neutral"
                
                topics = re.findall(r'#(\w+)', caption_lower)
                topics = list(dict.fromkeys(topics))[:3]
                
                views = 0
                
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
    if "imginn.com" in url or "cdninstagram.com" in url:
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

@app.get("/api/analyze/{handle}", response_model=ProfileAnalytics)
def analyze_profile(handle: str):
    clean_handle = handle.lower().replace("@", "").strip()
    if not clean_handle:
        raise HTTPException(status_code=400, detail="Invalid Instagram handle")
    
    # Check Cache
    now = time.time()
    if clean_handle in PROFILE_CACHE:
        expiry, cached_result = PROFILE_CACHE[clean_handle]
        if now < expiry:
            print(f"Cache Hit for {clean_handle}. Returning cached result.")
            return cached_result
        else:
            print(f"Cache expired for {clean_handle}. Re-fetching.")
            PROFILE_CACHE.pop(clean_handle, None)

    # 1. Try Live Scraping
    scraped = scrape_instagram_profile_live(clean_handle)
    if scraped:
        posts = []
        total_er = 0.0
        pos_count = 0
        neg_count = 0
        neu_count = 0
        topics_freq = {}
        
        for p in scraped["recent_posts"]:
            post_obj = PostDetail(
                id=p["id"],
                shortcode=p["shortcode"],
                caption=p["caption"],
                likes=p["likes"],
                comments=p["comments"],
                engagement_rate=p["engagement_rate"],
                sentiment=p["sentiment"],
                is_sponsored=p["is_sponsored"],
                topics=[],
                image_url=p["image_url"],
                created_at=p["created_at"],
                media_type=p["media_type"]
            )
            posts.append(post_obj)
            total_er += p["engagement_rate"]
            
            if p["sentiment"] == "positive":
                pos_count += 1
            elif p["sentiment"] == "negative":
                neg_count += 1
            else:
                neu_count += 1
                
            for t in p["topics"]:
                topics_freq[t] = topics_freq.get(t, 0) + 1
        
        avg_er = round(total_er / max(len(posts), 1), 2)
        
        expected_er = max(1.0, 5.0 - (scraped["followers"] / 1000000.0))
        if avg_er < expected_er:
            fake_follower_percentage = round(min(60.0, ((expected_er - avg_er) / expected_er) * 45.0), 1)
        else:
            fake_follower_percentage = round(min(5.0, 1.0 / max(avg_er, 0.1)), 1)
            
        total_posts_sentiment = max(pos_count + neg_count + neu_count, 1)
        sentiment_distribution = {
            "positive": round((pos_count / total_posts_sentiment) * 100.0, 1),
            "neutral": round((neu_count / total_posts_sentiment) * 100.0, 1),
            "negative": round((neg_count / total_posts_sentiment) * 100.0, 1)
        }
        
        brand_safety_score = round(100.0 - (sentiment_distribution["negative"] * 1.5), 1)
        brand_safety_score = max(min(brand_safety_score, 100.0), 50.0)
        
        dominant_topics = []
            
        # Separate Image vs Reel stats
        images_likes = [p["likes"] for p in scraped["recent_posts"] if p["media_type"] == "image"]
        images_comments = [p["comments"] for p in scraped["recent_posts"] if p["media_type"] == "image"]
        reels_likes = [p["likes"] for p in scraped["recent_posts"] if p["media_type"] == "video"]
        reels_comments = [p["comments"] for p in scraped["recent_posts"] if p["media_type"] == "video"]
        
        img_avg_likes = round(sum(images_likes) / len(images_likes), 1) if images_likes else 0.0
        img_avg_comments = round(sum(images_comments) / len(images_comments), 1) if images_comments else 0.0
        img_er = round(((img_avg_likes + img_avg_comments) / scraped["followers"]) * 100.0, 2) if scraped["followers"] > 0 else 0.0
        
        reels_avg_likes = round(sum(reels_likes) / len(reels_likes), 1) if reels_likes else 0.0
        reels_avg_comments = round(sum(reels_comments) / len(reels_comments), 1) if reels_comments else 0.0
        reels_er = round(((reels_avg_likes + reels_avg_comments) / scraped["followers"]) * 100.0, 2) if scraped["followers"] > 0 else 0.0
        
        # Reel views to followers ratio
        reels_views = [p["views"] for p in scraped["recent_posts"] if p["media_type"] == "video" and p.get("views", 0) > 0]
        reels_avg_views = sum(reels_views) / len(reels_views) if reels_views else 0.0
        reels_views_to_followers_ratio = round((reels_avg_views / max(scraped["followers"], 1)) * 100.0, 2) if scraped["followers"] > 0 else 0.0

        total_likes = sum(p["likes"] for p in scraped["recent_posts"])
        total_comments = sum(p["comments"] for p in scraped["recent_posts"])
        likes_to_comments_ratio = round(total_likes / max(total_comments, 1), 2)
        
        influence_score = round(min(max((scraped["followers"] ** 0.15) * (avg_er ** 0.4), 1.0), 10.0), 1)
        estimated_reach = int(scraped["followers"] * (avg_er / 100.0) * 2.5)
        estimated_reach = min(estimated_reach, scraped["followers"])
        estimated_reach = max(estimated_reach, int(scraped["followers"] * 0.05))
            
        result = ProfileAnalytics(
            handle=scraped["handle"],
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
            is_simulated=False,
            is_estimated=scraped.get("is_estimated", False)
        )
        
        # Cache successful scrape
        if scraped["followers"] > 0:
            PROFILE_CACHE[clean_handle] = (time.time() + CACHE_TTL, result)
        else:
            # Cache failure for just 10 seconds to avoid immediately hammering the source again
            PROFILE_CACHE[clean_handle] = (time.time() + 10, result)
            
        return result
    
    # 2. Fallback to empty metrics (no simulated/false data) if scraper fails completely
    fallback_result = ProfileAnalytics(
        handle=clean_handle,
        full_name="N/A",
        biography="Unable to fetch real-time data from Instagram.",
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
        is_simulated=False,
        is_estimated=False
    )
    # Cache temporary failure for 10 seconds
    PROFILE_CACHE[clean_handle] = (time.time() + 10, fallback_result)
    return fallback_result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
