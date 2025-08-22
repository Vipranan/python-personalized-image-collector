import os
import io
import requests
from urllib.parse import urljoin, urlparse
import streamlit as st
from bs4 import BeautifulSoup
from zipfile import ZipFile
from duckduckgo_search import DDGS

# --- Constants and Setup ---
SAVE_FOLDER = "images"
os.makedirs(SAVE_FOLDER, exist_ok=True)

# IMPROVEMENT 4: Add a User-Agent to mimic a browser and prevent blocking.
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# IMPROVEMENT 1: Centralized configuration for platforms. Makes adding new platforms trivial.
PLATFORMS = {
    "substack": {
        "url_template": lambda user: f"https://{user}.substack.com",
        "username_parser": lambda url: url.netloc.split('.')[0]
    },
    "medium": {
        "url_template": lambda user: f"https://medium.com/@{user.strip('@')}",
        "username_parser": lambda url: url.path.strip('/').replace('@', '')
    }
    # To add another platform, just add an entry here!
}

# --- Core Functions ---

def _extract_image_from_html(soup, base_url):
    """A robust, unified function to find the best profile image from page HTML."""
    # Priority: Open Graph -> Twitter Card -> Specific class -> Favicon
    og_image = soup.find("meta", property="og:image")
    if og_image and og_image.get("content"):
        return urljoin(base_url, og_image["content"])

    twitter_image = soup.find("meta", property="twitter:image")
    if twitter_image and twitter_image.get("content"):
        return urljoin(base_url, twitter_image["content"])

    profile_img = soup.find("img", class_=lambda x: x and "profile-image" in x)
    if profile_img and profile_img.get("src"):
        return urljoin(base_url, profile_img["src"])

    icon_link = soup.find("link", rel="icon")
    if icon_link and icon_link.get("href"):
        return urljoin(base_url, icon_link["href"])

    return None

@st.cache_data(show_spinner=False)
def find_profile_url_with_search(query, platform_name):
    """Uses DuckDuckGo to find a profile URL with a general search query."""
    st.info(f"Searching the web for '{query}' on {platform_name}...")
    site_domain = f"{platform_name.lower()}.com"
    try:
        search_query = f'"{query}" {platform_name} author profile'
        with DDGS() as ddgs:
            results = list(ddgs.text(search_query, max_results=5))
            for result in results:
                url = result.get('href')
                if url and site_domain in urlparse(url).netloc:
                    st.success(f"Found potential profile: {url}")
                    return url
    except Exception as e:
        st.warning(f"Web search encountered an error: {e}")

    st.warning(f"Could not find a likely profile for '{query}' in search results.")
    return None

# IMPROVEMENT 2: Cache the entire function for efficiency on repeated searches.
@st.cache_data(show_spinner=False)
def fetch_profile_image(user_input, platform):
    """
    Fetches and saves a profile image for a given user and platform.
    Returns a dictionary with image info or None on failure.
    """
    profile_url = None
    platform_config = PLATFORMS.get(platform)
    if not platform_config:
        st.error(f"Configuration for platform '{platform}' not found.")
        return None

    if user_input.startswith("http"):
        # Only process if the URL seems to belong to the selected platform
        if platform in urlparse(user_input).netloc:
             profile_url = user_input
        else:
            return None # Skip if URL doesn't match platform
    else:
        profile_url = platform_config["url_template"](user_input)

    try:
        response = requests.get(profile_url, timeout=10, allow_redirects=True, headers=HEADERS)
        final_url = response.url

        if response.status_code != 200:
            found_url = find_profile_url_with_search(user_input, platform.capitalize())
            if found_url:
                response = requests.get(found_url, timeout=10, allow_redirects=True, headers=HEADERS)
                final_url = response.url
            else:
                return None

        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

        soup = BeautifulSoup(response.text, "html.parser")
        img_url = _extract_image_from_html(soup, final_url)

        if not img_url:
            return None

        img_response = requests.get(img_url, timeout=10, headers=HEADERS)
        img_response.raise_for_status()

        # Use the platform-specific parser from the config
        parsed_url = urlparse(final_url)
        username = platform_config["username_parser"](parsed_url)

        filename = f"{platform}_{username}.jpg"
        filepath = os.path.join(SAVE_FOLDER, filename)

        with open(filepath, "wb") as f:
            f.write(img_response.content)
            
        return {
            "path": filepath,
            "filename": filename,
            "source_url": final_url
        }

    except requests.RequestException as e:
        st.error(f"A network error occurred for {profile_url}: {e}")
        return None

def zip_images(results_dict):
    """Creates a ZIP file in memory from a list of result dictionaries."""
    zip_buffer = io.BytesIO()
    filepaths_to_zip = set() # Use a set to avoid duplicates
    
    for query_results in results_dict.values():
        for result in query_results:
             filepaths_to_zip.add(result["path"])

    with ZipFile(zip_buffer, "w") as zip_file:
        for path in filepaths_to_zip:
            zip_file.write(path, arcname=os.path.basename(path))
    zip_buffer.seek(0)
    return zip_buffer


# --- Streamlit UI ---
st.set_page_config(page_title="Profile Image Finder", layout="wide")
st.title("Profile Image Finder 🕵️‍♂️")
st.markdown("Enter names, usernames, or full profile URLs. The app will search for them on the selected platforms.")

# Initialize session state
if "results" not in st.session_state:
    st.session_state.results = {}

c1, c2 = st.columns([2,1])

with c1:
    user_inputs = st.text_area(
        "Enter Names or URLs (one per line)",
        height=150,
        key="universal_input",
        placeholder="Casey Newton\n@barackobama\nhttps://stratechery.substack.com"
    )

with c2:
    selected_platforms_display = st.multiselect(
        "Select platforms to search on:",
        [p.capitalize() for p in PLATFORMS.keys()],
        default=[p.capitalize() for p in PLATFORMS.keys()]
    )
    selected_platforms = [p.lower() for p in selected_platforms_display]

    fetch_button = st.button("🚀 Fetch Profile Images", type="primary")
    # IMPROVEMENT 5: Added a dedicated clear button for better UX
    clear_button = st.button("🧹 Clear Results")

if clear_button:
    st.session_state.results = {}
    st.experimental_rerun()

if fetch_button:
    queries = [line.strip() for line in user_inputs.strip().splitlines() if line.strip()]

    if not queries:
        st.warning("Please enter at least one name or URL.")
    elif not selected_platforms:
        st.warning("Please select at least one platform to search.")
    else:
        for query in queries:
            if query not in st.session_state.results:
                 st.session_state.results[query] = []
            
            with st.spinner(f"Searching for '{query}'..."):
                found_on_any_platform = False
                for platform in selected_platforms:
                    result_info = fetch_profile_image(query, platform)
                    if result_info:
                        # Avoid adding duplicate results for the same query
                        if not any(r['path'] == result_info['path'] for r in st.session_state.results[query]):
                            st.session_state.results[query].append(result_info)
                        found_on_any_platform = True
                
                if not found_on_any_platform:
                    # To show that a search was attempted but failed
                    if not st.session_state.results[query]:
                         st.session_state.results[query] = "failed"


if st.session_state.results:
    st.markdown("--- \n ## Fetched Images")

    all_found_results = []
    
    # IMPROVEMENT 3: Use expanders for a cleaner UI layout.
    for query, results in st.session_state.results.items():
        with st.expander(f"Results for: **{query}**", expanded=True):
            if results == "failed":
                st.error("Could not find any images for this query.")
                continue
            
            if not results:
                st.info("Searching... (or no results yet)")
                continue

            cols = st.columns(4)
            for idx, result in enumerate(results):
                all_found_results.append(result)
                with cols[idx % 4]:
                    st.image(result["path"], caption=result['filename'])
                    st.markdown(f"[Source]({result['source_url']})")

    if all_found_results:
        zip_file = zip_images(st.session_state.results)
        st.download_button(
            "⬇️ Download All as ZIP",
            data=zip_file,
            file_name="profile_images.zip",
            mime="application/zip",
        )
    