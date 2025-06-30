import streamlit as st
import requests
import os
import time
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import re
from dotenv import load_dotenv
from duckduckgo_search import DDGS

class ProfileImageScraperStreamlit:
    def __init__(self):
        load_dotenv()  # Load .env file
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.207 Safari/537.36 Edg/124.0.2478.97'
        })
        # Add LinkedIn li_at cookie if available
        li_at = os.getenv("LI_AT")
        if li_at:
            self.session.cookies.set("li_at", li_at, domain=".linkedin.com")
        self.download_folder = "profile_images"
        os.makedirs(self.download_folder, exist_ok=True)
        self.log = []

    def log_message(self, message):
        self.log.append(f"{time.strftime('%H:%M:%S')} - {message}")

    def validate_image_url(self, url: str) -> bool:
        """Validate if URL points to an accessible image"""
        try:
            response = self.session.head(url, timeout=10)
            content_type = response.headers.get('content-type', '').lower()
            return response.status_code == 200 and 'image' in content_type
        except:
            return False

    def download_image(self, img_info: Dict, person_name: str) -> Optional[str]:
        """Download image and save to disk"""
        try:
            url = img_info['url']
            source = img_info['source']
            
            response = self.session.get(url, timeout=15)
            if response.status_code == 200:
                ext = '.jpg'
                if url.lower().endswith(('.png', '.gif', '.webp')):
                    ext = os.path.splitext(url.lower())[1]
                safe_name = re.sub(r'[<>:"/\\|?*]', '_', person_name)
                timestamp = int(time.time())
                filename = f"{safe_name}_{source.replace(' ', '_')}_{timestamp}{ext}"
                filepath = os.path.join(self.download_folder, filename)
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                return filepath
        except Exception as e:
            self.log_message(f"Error downloading image: {e}")
        return None

    def scrape_images(self, person_name, platforms, max_images):
        self.log = []
        all_images = []
        self.log_message(f"Starting scrape for: {person_name}")
        self.log_message(f"Max images: {max_images}")

        # DuckDuckGo image search
        duck_images = self.search_duckduckgo_images(person_name, max_images)
        all_images.extend(duck_images)
        self.log_message(f"Found {len(duck_images)} images from DuckDuckGo")

        # Validate and download
        valid_images = []
        for img in all_images:
            if self.validate_image_url(img['url']):
                valid_images.append(img)
                self.log_message(f"✓ Valid image from {img['source']}")
            else:
                self.log_message(f"✗ Invalid/inaccessible image from {img['source']}")

        downloaded_count = 0
        for i, img_info in enumerate(valid_images[:max_images]):
            filepath = self.download_image(img_info, person_name)
            if filepath:
                downloaded_count += 1
                self.log_message(f"✓ Downloaded: {os.path.basename(filepath)}")
            else:
                self.log_message(f"✗ Failed to download from {img_info['source']}")

        self.log_message(f"Scraping completed! Downloaded {downloaded_count} images.")
        return downloaded_count, self.log

    def search_duckduckgo_images(self, query: str, max_results: int = 5) -> List[Dict]:
        images = []
        try:
            with DDGS() as ddgs:
                for r in ddgs.images(query + " profile picture", max_results=max_results):
                    images.append({
                        'url': r['image'],
                        'source': 'DuckDuckGo Images',
                        'alt': r.get('title', ''),
                        'method': 'duckduckgo_search'
                    })
        except Exception as e:
            self.log_message(f"Error searching DuckDuckGo Images: {e}")
        return images

def main():
    st.set_page_config(page_title="Profile Image Scraper", layout="wide")
    st.title("📸 Profile Image Scraper (Streamlit Edition)")

    with st.sidebar:
        st.header("Configuration")
        person_name = st.text_input("Person Name", "")
        twitter = st.text_input("Twitter/X Username", "")
        github = st.text_input("GitHub Username", "")
        linkedin = st.text_input("LinkedIn URL or Username", "")
        substack = st.text_input("Substack Username or URL", "")
        medium = st.text_input("Medium Username or URL", "")
        max_images = st.number_input("Max Images", min_value=1, max_value=50, value=10)
        download_folder = st.text_input("Download Folder", "profile_images")
        start = st.button("Start Scraping")

    scraper = ProfileImageScraperStreamlit()
    scraper.download_folder = download_folder

    if start and person_name:
        platforms = {}
        if twitter: platforms['twitter'] = twitter
        if github: platforms['github'] = github
        if linkedin: platforms['linkedin'] = linkedin
        if substack: platforms['substack'] = substack
        if medium: platforms['medium'] = medium

        with st.spinner("Scraping in progress..."):
            count, logs = scraper.scrape_images(person_name, platforms, max_images)
        st.success(f"Scraping completed! Downloaded {count} images.")
        st.markdown("### Log")
        st.text("\n".join(logs))
        st.markdown(f"**Images saved to:** `{os.path.abspath(download_folder)}`")
    elif start:
        st.error("Please enter a person name.")

if __name__ == "__main__":
    main()