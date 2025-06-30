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

# ==== Streamlit UI ====
st.set_page_config(page_title="LinkedIn Profile Image Fetcher", layout="centered")
st.title("🔗 LinkedIn Profile Image Fetcher")

st.markdown("Paste **one or more LinkedIn profile URLs** below:")

input_urls = st.text_area("LinkedIn Profile URLs (one per line)", height=200)
start = st.button("Fetch Profile Images")

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

        if filepaths:
            zip_file = zip_images(filepaths)
            st.download_button(
                label="⬇️ Download All Images as ZIP",
                data=zip_file,
                file_name="linkedin_profile_images.zip",
                mime="application/zip"
            )
