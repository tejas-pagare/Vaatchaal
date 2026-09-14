"""
Image fetching service for travel destinations and itinerary landmarks.
Uses Unsplash (if key provided) with seamless fallback to Wikipedia Commons (no API key required).
"""

import os
import re
import urllib.parse
import httpx
from dotenv import load_dotenv

load_dotenv()

UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")

# Curated fallback high-quality destination photos
DEFAULT_TRAVEL_IMAGES = {
    "japan": "https://images.unsplash.com/photo-1503899036084-c55cdd92da26?auto=format&fit=crop&w=800&q=80",
    "tokyo": "https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?auto=format&fit=crop&w=800&q=80",
    "shibuya": "https://images.unsplash.com/photo-1542051841857-5f90071e7989?auto=format&fit=crop&w=800&q=80",
    "temple": "https://images.unsplash.com/photo-1578637387939-43c525550085?auto=format&fit=crop&w=800&q=80",
    "beach": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=800&q=80",
    "bali": "https://images.unsplash.com/photo-1537996194471-e657df975ab4?auto=format&fit=crop&w=800&q=80",
    "goa": "https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?auto=format&fit=crop&w=800&q=80",
    "paris": "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?auto=format&fit=crop&w=800&q=80",
    "default": "https://images.unsplash.com/photo-1488646953014-85cb44e25828?auto=format&fit=crop&w=800&q=80",
}


def _get_curated_fallback(query: str) -> str:
    query_lower = query.lower()
    for key, url in DEFAULT_TRAVEL_IMAGES.items():
        if key in query_lower:
            return url
    return DEFAULT_TRAVEL_IMAGES["default"]


async def fetch_place_image(place_name: str, destination: str = "") -> str:
    """
    Fetch an image URL for a place/landmark.
    1. Try Unsplash if API key is present.
    2. Try Wikipedia Page Summary Thumbnail (Free, no key needed).
    3. Try Wikimedia Commons Search.
    4. Fall back to curated aesthetic travel photo.
    """
    clean_query = f"{place_name} {destination}".strip()
    
    # 1. Unsplash (if configured)
    if UNSPLASH_ACCESS_KEY:
        try:
            url = "https://api.unsplash.com/search/photos"
            params = {
                "query": clean_query,
                "per_page": 1,
                "orientation": "landscape",
                "client_id": UNSPLASH_ACCESS_KEY,
            }
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, params=params, timeout=4.0)
                if resp.status_code == 200:
                    results = resp.json().get("results", [])
                    if results and "urls" in results[0]:
                        return results[0]["urls"]["regular"]
        except Exception:
            pass

    # 2. Wikipedia Summary REST API (Fast, reliable, free)
    try:
        wiki_title = re.sub(r"[^\w\s-]", "", place_name).strip().replace(" ", "_")
        wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(wiki_title)}"
        
        headers = {"User-Agent": "TravelPlannerAI/1.0 (travelplanner@example.com)"}
        async with httpx.AsyncClient() as client:
            resp = await client.get(wiki_url, headers=headers, timeout=3.5)
            if resp.status_code == 200:
                data = resp.json()
                # Check thumbnail or original image
                if "thumbnail" in data and "source" in data["thumbnail"]:
                    # Upgrade thumbnail size for sharp display
                    src = data["thumbnail"]["source"]
                    return re.sub(r"/\d+px-", "/800px-", src)
                elif "originalimage" in data and "source" in data["originalimage"]:
                    return data["originalimage"]["source"]
    except Exception:
        pass

    # 3. Wikipedia API Search query fallback
    try:
        search_term = urllib.parse.quote(f"{place_name}")
        search_api = f"https://en.wikipedia.org/w/api.php?action=query&format=json&prop=pageimages&pithumbsize=800&generator=search&gsrsearch={search_term}&gsrlimit=1"
        headers = {"User-Agent": "TravelPlannerAI/1.0 (travelplanner@example.com)"}
        async with httpx.AsyncClient() as client:
            resp = await client.get(search_api, headers=headers, timeout=3.5)
            if resp.status_code == 200:
                data = resp.json()
                pages = data.get("query", {}).get("pages", {})
                for _, page_info in pages.items():
                    if "thumbnail" in page_info:
                        return page_info["thumbnail"]["source"]
    except Exception:
        pass

    # 4. Curated fallback
    return _get_curated_fallback(clean_query)
