import streamlit as st
import os
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import json
from duckduckgo_search import DDGS

# --- Constants and Setup ---
SAVE_FOLDER = "images"
os.makedirs(SAVE_FOLDER, exist_ok=True)

if "scraped_profiles" not in st.session_state:
    st.session_state.scraped_profiles = []

# --- Core Functions ---
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
PLATFORMS = {
    "substack": {"url_template": lambda user: f"https://{user}.substack.com"},
    "medium": {"url_template": lambda user: f"https://medium.com/@{user.strip('@')}"}
}

def find_profile_url_with_search(query, platform_name):
    """Uses DuckDuckGo to find a profile URL by trying multiple search patterns."""
    st.info(f"Searching the web for '{query}' on {platform_name}...")
    site_domain = f"{platform_name.lower()}.com"
    search_queries = [
        f'"{query}" site:{site_domain}',
        f'"{query}" {platform_name} author profile'
    ]
    try:
        with DDGS() as ddgs:
            for i, search_query in enumerate(search_queries):
                st.write(f"Attempting search ({i+1}/2): `{search_query}`")
                results = list(ddgs.text(search_query, max_results=3))
                for result in results:
                    url = result.get('href')
                    if url and site_domain in urlparse(url).netloc:
                        path = urlparse(url).path
                        if len(path) > 1 and not any(page in path.lower() for page in ['/about', '/topics', '/search', '/tag']):
                            st.success(f"Found potential profile: {url}")
                            return url
    except Exception as e:
        st.warning(f"Web search encountered an error: {e}")
    st.warning(f"Could not find a likely profile for '{query}' in search results.")
    return None

def _extract_image_from_html(soup, base_url):
    """
    Finds the profile image by prioritizing specific classes before falling back to meta tags.
    """
    profile_img = soup.find("img", class_=lambda c: c and any(key in c for key in ["avatar", "profile", "author"]))
    if profile_img and profile_img.get("src"):
        return urljoin(base_url, profile_img["src"])
    og_image = soup.find("meta", property="og:image")
    if og_image and og_image.get("content"):
        return urljoin(base_url, og_image["content"])
    twitter_image = soup.find("meta", property="twitter:image")
    if twitter_image and twitter_image.get("content"):
        return urljoin(base_url, twitter_image["content"])
    icon_link = soup.find("link", rel="icon")
    if icon_link and icon_link.get("href"):
        return urljoin(base_url, icon_link["href"])
    return None

def _extract_display_name(soup):
    """Finds the display name using a priority list of common locations."""
    json_ld_script = soup.find("script", type="application/ld+json")
    if json_ld_script:
        try:
            data = json.loads(json_ld_script.string)
            if data.get("@type") == "ProfilePage" and data.get("mainEntity"):
                return data["mainEntity"].get("name", "").strip()
            if data.get("author") and data["author"].get("name"):
                return data["author"]["name"].strip()
        except (json.JSONDecodeError, AttributeError):
            pass
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        name = og_title["content"]
        og_site_name = soup.find("meta", property="og:site_name")
        if og_site_name and og_site_name.get("content"):
            name = name.replace(f"| {og_site_name['content']}", "")
            name = name.replace(f"- {og_site_name['content']}", "")
        return name.strip()
    h1_tag = soup.find("h1")
    if h1_tag and h1_tag.string:
        return h1_tag.string.strip()
    if soup.title and soup.title.string:
        return soup.title.string.split('|')[0].strip()
    return None

def fetch_profile_image(user_input, platform):
    """Fetches a profile image, using a direct guess first, then falling back to a web search."""
    profile_url = None
    if user_input.startswith("http"):
        profile_url = user_input
    elif ' ' in user_input or len(user_input) < 5:
        profile_url = find_profile_url_with_search(user_input, platform.capitalize())
    else:
        platform_config = PLATFORMS.get(platform)
        if platform_config:
            profile_url = platform_config["url_template"](user_input.lower())

    if not profile_url:
        st.error(f"Could not determine a URL for '{user_input}' on {platform}.")
        return None

    try:
        st.info(f"Attempting to fetch page: {profile_url}")
        response = requests.get(profile_url, timeout=10, allow_redirects=True, headers=HEADERS)
        if response.status_code != 200 and not user_input.startswith("http"):
            st.warning("Direct URL failed. Falling back to web search...")
            search_url = find_profile_url_with_search(user_input, platform.capitalize())
            if search_url:
                response = requests.get(search_url, timeout=10, allow_redirects=True, headers=HEADERS)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        img_url = _extract_image_from_html(soup, response.url)
        display_name = _extract_display_name(soup)
        
        if not img_url:
            st.warning(f"Could not find an image URL on {response.url}")
            return None
            
        img_response = requests.get(img_url, timeout=10, headers=HEADERS)
        img_response.raise_for_status()
        
        username = user_input.lower().split('.')[0].strip('@').replace(' ', '_')
        filename = f"{platform}_{username}.jpg"
        filepath = os.path.join(SAVE_FOLDER, filename)
        
        with open(filepath, "wb") as f:
            f.write(img_response.content)
            
        st.success(f"Saved: {display_name or filename}")
        
        return {
            "filepath": filepath,
            "display_name": display_name or user_input
        }
        
    except requests.RequestException as e:
        st.error(f"Failed to process '{user_input}'. Reason: {e}")
        return None

# --- Streamlit User Interface ---
st.set_page_config(page_title="Profile Image Finder", layout="wide")
st.title("Profile Image Finder 🕵️‍♂️")
st.markdown("Enter names, usernames, or full profile URLs. The app will search for them on the selected platforms.")

user_inputs = st.text_area(
    "Enter Names or URLs (one per line)",
    height=150,
    placeholder="Casey Newton\n@barackobama\nhttps://stratechery.substack.com"
)
selected_platforms_display = st.multiselect(
    "Select platforms to search on:",
    ['Substack', 'Medium'],
    default=['Substack', 'Medium']
)
selected_platforms = [p.lower() for p in selected_platforms_display]

if st.button("🚀 Fetch Profile Images", type="primary"):
    st.session_state.scraped_profiles.clear()
    queries = [line.strip() for line in user_inputs.strip().splitlines() if line.strip()]
    if not queries:
        st.warning("Please enter at least one name or URL.")
    elif not selected_platforms:
        st.warning("Please select at least one platform.")
    else:
        for query in queries:
            st.markdown(f"--- \n### Searching for: **{query}**")
            for platform in selected_platforms:
                with st.spinner(f"Checking {platform}..."):
                    profile_data = fetch_profile_image(query, platform)
                    if profile_data and profile_data not in st.session_state.scraped_profiles:
                        st.session_state.scraped_profiles.append(profile_data)

# --- Image Display Section ---
if st.session_state.scraped_profiles:
    st.markdown("--- \n## Fetched Images 🖼️")
    cols = st.columns(4)
    for idx, profile in enumerate(st.session_state.scraped_profiles):
        with cols[idx % 4]:
            st.image(profile["filepath"], caption=profile["display_name"], use_container_width=True)

