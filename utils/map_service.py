"""
Interactive Route Map Service using Folium / Leaflet.
Renders stylized vector route maps with numbered waypoint pins and connecting trails.
"""

import urllib.parse
import httpx
import folium

# Known landmark coordinate cache for fast instant rendering
COORDINATE_CACHE = {
    # Tokyo
    "tokyo": [35.6762, 139.6503],
    "shibuya": [35.6580, 139.7016],
    "shinjuku": [35.6938, 139.7034],
    "asakusa": [35.7118, 139.7967],
    "senso-ji": [35.7148, 139.7967],
    "ueno": [35.7141, 139.7741],
    "ginza": [35.6719, 139.7648],
    "harajuku": [35.6702, 139.7027],
    "meiji shrine": [35.6764, 139.6993],
    "tsukiji": [35.6655, 139.7707],
    "odaiba": [35.6266, 139.7741],
    "akihabara": [35.6983, 139.7731],
    "roppongi": [35.6628, 139.7314],
    
    # Paris
    "paris": [48.8566, 2.3522],
    "eiffel tower": [48.8584, 2.2945],
    "louvre": [48.8606, 2.3376],
    "notre dame": [48.8530, 2.3499],
    "montmartre": [48.8867, 2.3431],
    
    # Bali
    "bali": [-8.4095, 115.1889],
    "ubud": [-8.5069, 115.2625],
    "seminyak": [-8.6913, 115.1682],
    "canggu": [-8.6478, 115.1385],
    "uluwatu": [-8.8291, 115.0849],

    # Goa
    "goa": [15.2993, 74.1240],
    "panaji": [15.4909, 73.8278],
    "calangute": [15.5439, 73.7553],
    "baga": [15.5553, 73.7517],
    "anjuna": [15.5733, 73.7412],
}


def _lookup_coords(name: str, fallback_lat: float = 35.6762, fallback_lon: float = 139.6503):
    name_lower = name.lower()
    for k, coords in COORDINATE_CACHE.items():
        if k in name_lower:
            return coords
    
    # Slight jitter if multiple unknown spots to prevent stacking pins on top of each other
    import hashlib
    h = int(hashlib.md5(name.encode()).hexdigest(), 16)
    offset_lat = ((h % 100) - 50) * 0.003
    offset_lon = (((h // 100) % 100) - 50) * 0.003
    return [fallback_lat + offset_lat, fallback_lon + offset_lon]


def generate_itinerary_map_html(destination: str, days: list[dict]) -> str:
    """
    Generate an interactive Leaflet route map HTML string.
    Features:
    - Numbered dark circle markers for each day
    - Connecting curved route polyline trail
    - Popup preview with photo, day title, and tags
    """
    if not days:
        return ""

    # Find center location
    center_coords = _lookup_coords(destination, 35.6762, 139.6503)
    
    # Extract points
    route_points = []
    markers_data = []

    for idx, day_info in enumerate(days, start=1):
        day_num = day_info.get("day", idx)
        title = day_info.get("title", f"Day {day_num}")
        tags = day_info.get("tags", ["Sightseeing"])
        img_url = day_info.get("image_url", "")
        
        search_q = day_info.get("search_query", title)
        coords = _lookup_coords(search_q, center_coords[0], center_coords[1])
        
        # If this is the first point, re-center map near it
        if idx == 1:
            center_coords = coords

        route_points.append(coords)
        markers_data.append({
            "day": day_num,
            "title": title,
            "coords": coords,
            "tags": tags,
            "image": img_url,
        })

    # Create Folium Map
    m = folium.Map(
        location=center_coords,
        zoom_start=12,
        tiles="CartoDB positron",
        control_scale=True,
    )

    # Add Route Trail (polyline)
    if len(route_points) > 1:
        folium.PolyLine(
            locations=route_points,
            color="#111827",
            weight=3.5,
            opacity=0.85,
            dash_array="6, 6",
            tooltip="Itinerary Route Trail",
        ).add_to(m)

    # Add Numbered Custom Markers
    for marker in markers_data:
        lat, lon = marker["coords"]
        day_num = marker["day"]
        title = marker["title"]
        img_tag = f'<img src="{marker["image"]}" style="width:100%; height:90px; object-fit:cover; border-radius:6px; margin-bottom:6px;"/>' if marker["image"] else ''
        tags_str = " ".join([f'<span style="background:#F3F4F6; color:#374151; padding:2px 6px; border-radius:999px; font-size:10px; margin-right:4px;">{t}</span>' for t in marker["tags"]])

        popup_html = f"""
        <div style="font-family:'Plus Jakarta Sans',sans-serif; width:180px;">
            {img_tag}
            <div style="font-weight:700; font-size:12px; color:#111827; margin-bottom:4px;">Day {day_num}: {title}</div>
            <div>{tags_str}</div>
        </div>
        """

        custom_icon = folium.DivIcon(
            html=f"""
            <div style="
                background-color:#111827;
                color:#FFFFFF;
                width:26px;
                height:26px;
                border-radius:50%;
                display:flex;
                align-items:center;
                justify-content:center;
                font-weight:800;
                font-size:11px;
                font-family:sans-serif;
                border:2px solid #FFFFFF;
                box-shadow:0 3px 8px rgba(0,0,0,0.3);
            ">{day_num}</div>
            """,
            icon_size=(26, 26),
            icon_anchor=(13, 13),
        )

        folium.Marker(
            location=[lat, lon],
            icon=custom_icon,
            popup=folium.Popup(popup_html, max_width=220),
            tooltip=f"Day {day_num}: {title}",
        ).add_to(m)

    return m._repr_html_()
