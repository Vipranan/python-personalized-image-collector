import os
import time
import io
import requests
import streamlit as st
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from zipfile import ZipFile

# Load li_at cookie from .env
load_dotenv()
LI_AT_COOKIE = os.getenv("LI_AT")
SAVE_FOLDER = "images"
os.makedirs(SAVE_FOLDER, exist_ok=True)

def fetch_profile_image(profile_url):
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(service=Service(), options=chrome_options)
    try:
        driver.get("https://www.linkedin.com")
        time.sleep(1)
        driver.add_cookie({"name": "li_at", "value": LI_AT_COOKIE, "domain": ".linkedin.com"})
        driver.get(profile_url)
        time.sleep(5)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
    finally:
        driver.quit()

    # Find image tag
    img_tag = soup.find("img", {
        "class": lambda x: x and (
            "profile-photo-edit__preview" in x or 
            "pv-top-card-profile-picture__image" in x or 
            "ivm-view-attr__img--centered" in x or 
            "artdeco-entity-image" in x
        )
    })

    if not img_tag or not img_tag.get("src"):
        return None, None

    img_url = img_tag.get("src")
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Cookie": f"li_at={LI_AT_COOKIE}"
    }

    response = requests.get(img_url, headers=headers)
    if response.status_code == 200:
        username = profile_url.strip('/').split('/')[-1]
        filename = f"{username}.jpg"
        filepath = os.path.join(SAVE_FOLDER, filename)
        with open(filepath, "wb") as f:
            f.write(response.content)
        return filename, filepath
    else:
        return None, None

def zip_images(filepaths):
    zip_buffer = io.BytesIO()
    with ZipFile(zip_buffer, "w") as zip_file:
        for path in filepaths:
            zip_file.write(path, arcname=os.path.basename(path))
    zip_buffer.seek(0)
    return zip_buffer

def fetch_substack_profile_image(profile_url):
    """
    Fetches the profile image from a Substack profile URL or username.
    Returns (filename, filepath) or (None, None) on failure.
    """
    try:
        # Normalize input: allow username or full URL
        if not profile_url.startswith("http"):
            profile_url = f"https://{profile_url}.substack.com/"
        if not profile_url.endswith("/"):
            profile_url += "/"
        response = requests.get(profile_url, timeout=10)
        if response.status_code != 200:
            return None, None
        soup = BeautifulSoup(response.text, "html.parser")
        img_url = None

        # Try <img class="profile-image">
        img_tag = soup.find("img", class_="profile-image")
        if img_tag and img_tag.get("src"):
            img_url = img_tag["src"]

        # Try Open Graph image
        if not img_url:
            og_img = soup.find("meta", property="og:image")
            if og_img and og_img.get("content"):
                img_url = og_img["content"]

        # Try favicon as fallback (sometimes used as profile image)
        if not img_url:
            icon_link = soup.find("link", rel="icon")
            if icon_link and icon_link.get("href"):
                img_url = icon_link["href"]
                # Make absolute if needed
                if img_url.startswith("/"):
                    img_url = profile_url.rstrip("/") + img_url

        # Try any <img> with likely profile image in src
        if not img_url:
            img_tag = soup.find("img", src=lambda x: x and ("profile" in x or "avatar" in x))
            if img_tag and img_tag.get("src"):
                img_url = img_tag["src"]

        if not img_url:
            return None, None

        # Download image
        img_response = requests.get(img_url, timeout=10)
        if img_response.status_code == 200:
            username = profile_url.split("//")[-1].split(".")[0]
            filename = f"substack_{username}.jpg"
            filepath = os.path.join(SAVE_FOLDER, filename)
            with open(filepath, "wb") as f:
                f.write(img_response.content)
            return filename, filepath
        else:
            return None, None
    except Exception as e:
        return None, None

def fetch_medium_profile_image(profile_url):
    """
    Fetches the profile image from a Medium profile URL or username.
    Returns (filename, filepath) or (None, None) on failure.
    """
    try:
        # Normalize URL
        if not profile_url.startswith("http"):
            profile_url = f"https://medium.com/@{profile_url.strip('@')}"
        if not profile_url.endswith("/"):
            profile_url += "/"
        response = requests.get(profile_url, timeout=10, allow_redirects=True)
        if response.status_code != 200:
            return None, None
        soup = BeautifulSoup(response.text, "html.parser")
        img_url = None

        # Try avatar-image class
        img_tag = soup.find("img", class_="avatar-image")
        if img_tag and img_tag.get("src"):
            img_url = img_tag["src"]

        # Try Open Graph image
        if not img_url:
            og_img = soup.find("meta", property="og:image")
            if og_img and og_img.get("content"):
                img_url = og_img["content"]

        # Try any image with medium.com/v2/resize: in src
        if not img_url:
            img_tag = soup.find("img", src=lambda x: x and "medium.com/v2/resize:" in x)
            if img_tag and img_tag.get("src"):
                img_url = img_tag["src"]

        # Fallback: any image with alt containing username
        if not img_url:
            username = profile_url.strip('/').split('/')[-1].strip('@')
            img_tag = soup.find("img", alt=lambda x: x and username.lower() in x.lower())
            if img_tag and img_tag.get("src"):
                img_url = img_tag["src"]

        if not img_url:
            return None, None

        # Download image
        img_response = requests.get(img_url, timeout=10)
        if img_response.status_code == 200:
            username = profile_url.strip('/').split('/')[-1].strip('@')
            filename = f"medium_{username}.jpg"
            filepath = os.path.join(SAVE_FOLDER, filename)
            with open(filepath, "wb") as f:
                f.write(img_response.content)
            return filename, filepath
        else:
            return None, None
    except Exception as e:
        return None, None

# ==== LinkedIn UI ====
st.set_page_config(page_title="LinkedIn Profile Image Fetcher", layout="centered")
st.title("🔗 LinkedIn Profile Image Fetcher")

st.markdown("Paste **one or more LinkedIn profile URLs** below:")

input_urls = st.text_area("LinkedIn Profile URLs (one per line)", height=200)
start = st.button("Fetch Profile Images")

# Use session state to persist LinkedIn filepaths
if "linkedin_filepaths" not in st.session_state:
    st.session_state.linkedin_filepaths = []

if start:
    urls = [url.strip() for url in input_urls.strip().splitlines() if url.strip()]
    if not LI_AT_COOKIE:
        st.error("`li_at` cookie not found in `.env` file.")
    elif not urls:
        st.warning("Please enter at least one LinkedIn profile URL.")
    else:
        filepaths = []
        for url in urls:
            with st.spinner(f"Fetching image for: {url}"):
                filename, path = fetch_profile_image(url)
                if filename:
                    filepaths.append(path)
                    st.image(path, caption=filename, width=200)
                else:
                    st.warning(f"❌ Failed to fetch image for: {url}")
        st.session_state.linkedin_filepaths = filepaths

# Always display previously fetched LinkedIn images and ZIP download
if st.session_state.linkedin_filepaths:
    st.markdown("### Previously Fetched LinkedIn Images")
    for path in st.session_state.linkedin_filepaths:
        st.image(path, caption=os.path.basename(path), width=200)
    zip_file = zip_images(st.session_state.linkedin_filepaths)
    st.download_button(
        label="⬇️ Download All Images as ZIP",
        data=zip_file,
        file_name="linkedin_profile_images.zip",
        mime="application/zip"
    )

# ==== Substack UI ====
st.markdown("---")
st.title("📰 Substack Profile Image Fetcher")

st.markdown("Paste **one or more Substack profile URLs or usernames** below:")

input_substack_urls = st.text_area("Substack Profile URLs or Usernames (one per line)", height=150, key="substack")
start_substack = st.button("Fetch Substack Images")

if "substack_filepaths" not in st.session_state:
    st.session_state.substack_filepaths = []

def substack_url_from_input(text):
    text = text.strip()
    if not text:
        return None
    if text.startswith("http"):
        return text
    # Assume username
    return f"https://{text}.substack.com/"

if start_substack:
    substack_inputs = [line.strip() for line in input_substack_urls.strip().splitlines() if line.strip()]
    substack_urls = [substack_url_from_input(x) for x in substack_inputs if substack_url_from_input(x)]
    if not substack_urls:
        st.warning("Please enter at least one Substack profile URL or username.")
    else:
        substack_filepaths = []
        for url in substack_urls:
            with st.spinner(f"Fetching image for: {url}"):
                filename, path = fetch_substack_profile_image(url)
                if filename:
                    substack_filepaths.append(path)
                    st.image(path, caption=filename, width=200)
                else:
                    st.warning(f"❌ Failed to fetch image for: {url}")
        st.session_state.substack_filepaths = substack_filepaths

if st.session_state.substack_filepaths:
    st.markdown("### Previously Fetched Substack Images")
    for path in st.session_state.substack_filepaths:
        st.image(path, caption=os.path.basename(path), width=200)
    zip_file = zip_images(st.session_state.substack_filepaths)
    st.download_button(
        label="⬇️ Download All Substack Images as ZIP",
        data=zip_file,
        file_name="substack_profile_images.zip",
        mime="application/zip"
    )

# ==== Medium UI ====
st.markdown("---")
st.title("✍️ Medium Profile Image Fetcher")

st.markdown("Paste **one or more Medium profile URLs or usernames** below:")

input_medium_urls = st.text_area("Medium Profile URLs or Usernames (one per line)", height=150, key="medium")
start_medium = st.button("Fetch Medium Images")

if "medium_filepaths" not in st.session_state:
    st.session_state.medium_filepaths = []

def medium_url_from_input(text):
    text = text.strip()
    if not text:
        return None
    if text.startswith("http"):
        return text
    # Assume username
    return f"https://medium.com/@{text}"

if start_medium:
    medium_inputs = [line.strip() for line in input_medium_urls.strip().splitlines() if line.strip()]
    medium_urls = [medium_url_from_input(x) for x in medium_inputs if medium_url_from_input(x)]
    if not medium_urls:
        st.warning("Please enter at least one Medium profile URL or username.")
    else:
        medium_filepaths = []
        for url in medium_urls:
            with st.spinner(f"Fetching image for: {url}"):
                filename, path = fetch_medium_profile_image(url)
                if filename:
                    medium_filepaths.append(path)
                    st.image(path, caption=filename, width=200)
                else:
                    st.warning(f"❌ Failed to fetch image for: {url}")
        st.session_state.medium_filepaths = medium_filepaths

if st.session_state.medium_filepaths:
    st.markdown("### Previously Fetched Medium Images")
    for path in st.session_state.medium_filepaths:
        st.image(path, caption=os.path.basename(path), width=200)
    zip_file = zip_images(st.session_state.medium_filepaths)
    st.download_button(
        label="⬇️ Download All Medium Images as ZIP",
        data=zip_file,
        file_name="medium_profile_images.zip",
        mime="application/zip"
    )