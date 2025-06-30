import streamlit as st
import requests
import os
import time
import hashlib
from urllib.parse import urljoin, urlparse, quote_plus
from bs4 import BeautifulSoup
import json
from typing import List, Dict, Optional
from PIL import Image
import io
import re
from pathlib import Path
import base64
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

class EnhancedProfileImageCollector:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none'
        })
        
    def log_message(self, message: str, msg_type: str = "info"):
        """Display log messages in Streamlit"""
        if msg_type == "success":
            st.success(f"✅ {message}")
        elif msg_type == "error":
            st.error(f"❌ {message}")
        elif msg_type == "warning":
            st.warning(f"⚠️ {message}")
        else:
            st.info(f"ℹ️ {message}")
    
    def is_valid_image_url(self, url: str) -> bool:
        """Quick validation for image URLs"""
        if not url or not url.startswith('http'):
            return False
        
        # Check if URL has image extension
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
        url_lower = url.lower()
        
        if any(ext in url_lower for ext in image_extensions):
            return True
            
        # Check for common image hosting domains
        image_domains = ['imgur.com', 'github.com', 'githubusercontent.com', 'twimg.com', 
                        'pbs.twimg.com', 'media.licdn.com', 'avatars.githubusercontent.com']
        
        return any(domain in url_lower for domain in image_domains)
    
    def validate_image_url(self, url: str) -> bool:
        """Validate if URL is accessible and contains an image"""
        try:
            if not self.is_valid_image_url(url):
                return False
                
            response = self.session.head(url, timeout=8, allow_redirects=True)
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '').lower()
                if any(img_type in content_type for img_type in ['image/', 'jpeg', 'jpg', 'png', 'gif', 'webp']):
                    return True
            return False
        except:
            return False
    
    def scrape_github_profile(self, username: str) -> Optional[Dict]:
        """Get GitHub profile image using API - Most reliable method"""
        try:
            st.write(f"🔍 Checking GitHub for: **{username}**")
            api_url = f"https://api.github.com/users/{username}"
            
            response = self.session.get(api_url, timeout=10)
            
            if response.status_code == 200:
                user_data = response.json()
                avatar_url = user_data.get('avatar_url')
                
                if avatar_url:
                    # Get maximum quality version
                    if '?' in avatar_url:
                        avatar_url = avatar_url.split('?')[0] + '?s=460'
                    else:
                        avatar_url += '?s=460'
                    
                    st.write(f"✅ Found GitHub avatar: {avatar_url}")
                    return {
                        'url': avatar_url,
                        'source': 'GitHub',
                        'username': username,
                        'name': user_data.get('name', username),
                        'quality': 'high',
                        'verified': True
                    }
            elif response.status_code == 404:
                st.write(f"⚠️ GitHub user '{username}' not found")
            else:
                st.write(f"⚠️ GitHub API error: {response.status_code}")
                
        except Exception as e:
            st.write(f"❌ GitHub error: {str(e)}")
        
        return None
    
    def scrape_twitter_profile(self, username: str) -> Optional[Dict]:
        """Enhanced Twitter/X profile scraping"""
        try:
            username = username.replace('@', '').strip()
            st.write(f"🔍 Checking Twitter/X for: **{username}**")
            
            # Try multiple URL formats
            urls = [
                f"https://nitter.net/{username}",  # Nitter proxy - often works better
                f"https://x.com/{username}",
                f"https://twitter.com/{username}"
            ]
            
            for url in urls:
                try:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Referer': 'https://google.com/'
                    }
                    
                    response = self.session.get(url, headers=headers, timeout=12, allow_redirects=True)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # Multiple extraction methods
                        selectors = [
                            'meta[property="og:image"]',
                            'meta[name="twitter:image"]',
                            'img[src*="profile_images"]',
                            'img[alt*="profile"]',
                            '.profile-picture img',
                            '.avatar img'
                        ]
                        
                        for selector in selectors:
                            try:
                                if selector.startswith('meta'):
                                    element = soup.select_one(selector)
                                    if element:
                                        img_url = element.get('content')
                                else:
                                    element = soup.select_one(selector)
                                    if element:
                                        img_url = element.get('src') or element.get('data-src')
                                
                                if img_url and ('twimg.com' in img_url or 'nitter' in img_url):
                                    # Enhance quality
                                    img_url = img_url.replace('_normal', '_400x400').replace('_bigger', '_400x400')
                                    if self.is_valid_image_url(img_url):
                                        st.write(f"✅ Found Twitter/X avatar: {img_url}")
                                        return {
                                            'url': img_url,
                                            'source': 'Twitter/X',
                                            'username': username,
                                            'quality': 'high',
                                            'verified': True
                                        }
                            except:
                                continue
                        
                        if 'nitter' not in url:  # Don't spam if using nitter
                            time.sleep(2)
                        break
                        
                except Exception as e:
                    st.write(f"🔍 Trying next Twitter URL... ({str(e)[:50]})")
                    continue
                    
        except Exception as e:
            st.write(f"❌ Twitter/X error: {str(e)}")
        
        return None
    
    def scrape_linkedin_profile(self, profile_input: str) -> Optional[Dict]:
        """Enhanced LinkedIn profile scraping"""
        try:
            # Handle different input formats
            if not profile_input.startswith('http'):
                if '/' in profile_input:
                    profile_url = f"https://www.linkedin.com/in/{profile_input}"
                else:
                    profile_url = f"https://www.linkedin.com/in/{profile_input}/"
            else:
                profile_url = profile_input
            
            st.write(f"🔍 Checking LinkedIn: **{profile_url}**")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': 'https://www.google.com/',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            response = self.session.get(profile_url, headers=headers, timeout=15, allow_redirects=True)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Multiple extraction methods for LinkedIn
                selectors = [
                    'meta[property="og:image"]',
                    'img.profile-photo-edit__preview',
                    'img[data-ghost-classes*="profile-photo"]',
                    'img.pv-top-card-profile-picture__image',
                    'img.pv-top-card__photo',
                    'button[aria-label*="profile photo"] img',
                    '.profile-photo img',
                    '.pv-top-card-profile-picture img'
                ]
                
                for selector in selectors:
                    try:
                        if selector.startswith('meta'):
                            element = soup.select_one(selector)
                            if element:
                                img_url = element.get('content')
                        else:
                            element = soup.select_one(selector)
                            if element:
                                img_url = element.get('src') or element.get('data-src') or element.get('data-delayed-url')
                        
                        if img_url and 'media.licdn.com' in img_url and self.is_valid_image_url(img_url):
                            st.write(f"✅ Found LinkedIn avatar: {img_url}")
                            return {
                                'url': img_url,
                                'source': 'LinkedIn',
                                'profile_url': profile_url,
                                'quality': 'medium',
                                'verified': True
                            }
                    except:
                        continue
                        
        except Exception as e:
            st.write(f"❌ LinkedIn error: {str(e)}")
        
        return None
    
    def search_bing_images(self, person_name: str, max_results: int = 8) -> List[Dict]:
        """Search Bing Images - Often more reliable than Google"""
        images = []
        try:
            st.write(f"🔍 Searching Bing Images for: **{person_name}**")
            
            search_queries = [
                f'"{person_name}" profile picture',
                f'{person_name} headshot photo',
                f'{person_name} portrait professional'
            ]
            
            for query in search_queries[:2]:
                try:
                    encoded_query = quote_plus(query)
                    search_url = f"https://www.bing.com/images/search?q={encoded_query}&form=HDRSC2&first=1&tsc=ImageBasicHover"
                    
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Referer': 'https://www.bing.com/'
                    }
                    
                    response = self.session.get(search_url, headers=headers, timeout=15)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # Bing image containers
                        img_containers = soup.find_all('a', class_='iusc')
                        
                        for container in img_containers:
                            if len(images) >= max_results:
                                break
                            
                            # Extract image data from 'm' attribute
                            m_data = container.get('m')
                            if m_data:
                                try:
                                    img_info = json.loads(m_data)
                                    img_url = img_info.get('murl')
                                    
                                    if img_url and self.is_valid_image_url(img_url):
                                        # Avoid duplicates
                                        if not any(img['url'] == img_url for img in images):
                                            images.append({
                                                'url': img_url,
                                                'source': 'Bing Images',
                                                'title': img_info.get('t', ''),
                                                'quality': 'medium'
                                            })
                                            st.write(f"✅ Found Bing image: {img_url[:60]}...")
                                except:
                                    continue
                    
                    time.sleep(2)  # Rate limiting
                    
                except Exception as e:
                    st.write(f"🔍 Bing search error: {str(e)[:50]}")
                    continue
                    
        except Exception as e:
            st.write(f"❌ Bing search failed: {str(e)}")
        
        return images
    
    def search_duckduckgo_images(self, person_name: str, max_results: int = 6) -> List[Dict]:
        """Enhanced DuckDuckGo image search"""
        images = []
        try:
            st.write(f"🔍 Searching DuckDuckGo for: **{person_name}**")
            
            # Get search page to extract vqd token
            search_url = f"https://duckduckgo.com/?q={quote_plus(person_name + ' profile picture')}&iar=images&iax=images&ia=images"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9'
            }
            
            response = self.session.get(search_url, headers=headers, timeout=12)
            
            if response.status_code == 200:
                # Extract vqd token
                vqd_match = re.search(r'vqd="([^"]+)"', response.text)
                if vqd_match:
                    vqd = vqd_match.group(1)
                    
                    # Use DDG images API
                    api_url = f"https://duckduckgo.com/i.js"
                    params = {
                        'l': 'us-en',
                        'o': 'json',
                        'q': f'{person_name} profile picture',
                        'vqd': vqd,
                        'f': ',,,,,',
                        'p': '1'
                    }
                    
                    api_response = self.session.get(api_url, params=params, headers=headers, timeout=10)
                    
                    if api_response.status_code == 200:
                        try:
                            data = api_response.json()
                            results = data.get('results', [])
                            
                            for result in results[:max_results]:
                                img_url = result.get('image')
                                if img_url and self.is_valid_image_url(img_url):
                                    images.append({
                                        'url': img_url,
                                        'source': 'DuckDuckGo',
                                        'title': result.get('title', ''),
                                        'quality': 'medium'
                                    })
                                    st.write(f"✅ Found DDG image: {img_url[:60]}...")
                        except Exception as e:
                            st.write(f"🔍 DDG API parsing error: {str(e)}")
                
                # Fallback: extract from page HTML
                if not images:
                    img_pattern = r'https://[^"\s,]+\.(?:jpg|jpeg|png|gif|webp)'
                    found_urls = re.findall(img_pattern, response.text, re.IGNORECASE)
                    
                    for url in found_urls[:max_results]:
                        if self.is_valid_image_url(url):
                            images.append({
                                'url': url,
                                'source': 'DuckDuckGo',
                                'quality': 'medium'
                            })
                            st.write(f"✅ Found DDG fallback image: {url[:60]}...")
                            
        except Exception as e:
            st.write(f"❌ DuckDuckGo search error: {str(e)}")
        
        return images
    
    def download_image(self, image_info: Dict, person_name: str, download_folder: str) -> Optional[str]:
        """Download and save image with better error handling"""
        try:
            st.write(f"⬇️ Downloading from {image_info['source']}: {image_info['url'][:50]}...")
            
            response = self.session.get(image_info['url'], stream=True, timeout=20)
            response.raise_for_status()
            
            # Verify it's actually an image
            content_type = response.headers.get('content-type', '')
            if not any(img_type in content_type.lower() for img_type in ['image/', 'jpeg', 'jpg', 'png', 'gif', 'webp']):
                st.write(f"⚠️ Not an image file: {content_type}")
                return None
            
            # Create folder structure
            person_folder = Path(download_folder) / person_name.replace(' ', '_').replace('/', '_')
            person_folder.mkdir(parents=True, exist_ok=True)
            
            # Generate safe filename
            url_hash = hashlib.md5(image_info['url'].encode()).hexdigest()[:8]
            source = re.sub(r'[^a-zA-Z0-9_-]', '_', image_info['source'])
            
            # Determine extension from content type
            if 'jpeg' in content_type or 'jpg' in content_type:
                ext = '.jpg'
            elif 'png' in content_type:
                ext = '.png'
            elif 'gif' in content_type:
                ext = '.gif'
            elif 'webp' in content_type:
                ext = '.webp'
            else:
                ext = '.jpg'
            
            filename = f"{source}_{url_hash}{ext}"
            filepath = person_folder / filename
            
            # Save image
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Verify file was created and has content
            if filepath.exists() and filepath.stat().st_size > 1000:  # At least 1KB
                st.write(f"✅ Saved: {filename}")
                return str(filepath)
            else:
                st.write(f"⚠️ File too small or failed to save")
                return None
                
        except Exception as e:
            st.write(f"❌ Download failed: {str(e)}")
            return None
    
    def collect_images(self, person_name: str, platforms: Dict, download_folder: str, max_images: int = 10):
        """Highly efficient collection with parallel processing and deduplication"""
        all_images = []
        seen_urls = set()

        st.write("### 🚀 Starting Image Collection...")

        # Phase 1: Platform-specific (serial, as these are few and high quality)
        st.write("#### Phase 1: Platform-specific searches")
        platform_funcs = [
            ('github', self.scrape_github_profile, platforms.get('github')),
            ('twitter', self.scrape_twitter_profile, platforms.get('twitter')),
            ('linkedin', self.scrape_linkedin_profile, platforms.get('linkedin'))
        ]
        for name, func, arg in platform_funcs:
            if arg:
                img = func(arg)
                if img and img['url'] not in seen_urls:
                    all_images.append(img)
                    seen_urls.add(img['url'])
                if len(all_images) >= max_images:
                    break

        # Phase 2: Search engines (parallel)
        if len(all_images) < max_images:
            st.write("#### Phase 2: Search engine queries (parallelized)")
            search_funcs = [
                (self.search_bing_images, person_name, max_images - len(all_images)),
                (self.search_duckduckgo_images, person_name, max_images - len(all_images))
            ]
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(func, arg, n) for func, arg, n in search_funcs]
                for future in as_completed(futures):
                    try:
                        results = future.result()
                        for img in results:
                            if img['url'] not in seen_urls and len(all_images) < max_images:
                                all_images.append(img)
                                seen_urls.add(img['url'])
                            if len(all_images) >= max_images:
                                break
                    except Exception as e:
                        st.write(f"❌ Search engine error: {e}")

        st.write(f"### 📊 Total unique images found: {len(all_images)}")

        # Phase 3: Download images (parallel)
        downloaded_files = []
        if all_images:
            st.write("#### Phase 3: Downloading images (parallelized)")
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = [
                    executor.submit(self.download_image, img_info, person_name, download_folder)
                    for img_info in all_images[:max_images]
                ]
                for future in as_completed(futures):
                    filepath = future.result()
                    if filepath:
                        downloaded_files.append(filepath)
            st.write(f"### ✅ Download Complete: {len(downloaded_files)} images saved")
            return downloaded_files
        else:
            st.write("### ❌ No images found")
            return []

def main():
    st.set_page_config(
        page_title="Enhanced Profile Image Collector",
        page_icon="🖼️",
        layout="wide"
    )
    
    st.title("🖼️ Enhanced Profile Image Collector")
    st.markdown("*Efficiently collect profile images from multiple platforms*")
    st.markdown("---")
    
    # Initialize collector
    if 'collector' not in st.session_state:
        st.session_state.collector = EnhancedProfileImageCollector()
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Person name
        person_name = st.text_input("👤 Person Name *", placeholder="Enter full name", help="Required field")
        
        # Platform usernames
        st.subheader("🌐 Platform Accounts")
        github_username = st.text_input("GitHub Username", placeholder="octocat", help="Just the username")
        linkedin_url = st.text_input("LinkedIn Profile", placeholder="john-doe-123456 or full URL", help="Username or full URL")
        twitter_username = st.text_input("Twitter/X Username", placeholder="elonmusk", help="With or without @")
        
        # Download settings
        st.subheader("📁 Download Settings")
        
        # Folder selection with browse option
        col1, col2 = st.columns([3, 1])
        with col1:
            download_folder = st.text_input("Download Folder", value="profile_images")
        with col2:
            if st.button("📂", help="Current folder browser"):
                st.info(f"Current: {os.getcwd()}")
        
        max_images = st.slider("Max Images", min_value=1, max_value=25, value=12, help="Maximum images to download")
        
        # Start button
        start_collection = st.button("🚀 Start Collection", type="primary", use_container_width=True)
        
        # AI Enhancement section
        st.markdown("---")
        st.subheader("🤖 AI Enhancement Options")
        st.markdown("""
        **Free AI APIs you can integrate:**
        
        🔹 **Hugging Face** (Free tier)
        - Face detection & cropping
        - Image quality enhancement
        - Background removal
        
        🔹 **Replicate** (Free credits)
        - Image upscaling
        - Face restoration
        - Style transfer
        
        🔹 **DeepAI** (Free tier)
        - Image colorization
        - Super resolution
        - Face enhancement
        
        🔹 **Remove.bg API** (Free quota)
        - Background removal
        - Professional headshots
        """)
    
    # Main area
    if start_collection:
        if not person_name.strip():
            st.error("❌ Please enter a person name!")
        else:
            # Create download folder
            try:
                os.makedirs(download_folder, exist_ok=True)
                st.success(f"📁 Download folder ready: {download_folder}")
            except Exception as e:
                st.error(f"❌ Cannot create folder: {str(e)}")
                return
            
            # Prepare platforms
            platforms = {}
            if github_username.strip():
                platforms['github'] = github_username.strip()
            if linkedin_url.strip():
                platforms['linkedin'] = linkedin_url.strip()
            if twitter_username.strip():
                platforms['twitter'] = twitter_username.strip().replace('@', '')
            
            st.write(f"**Target:** {person_name}")
            if platforms:
                st.write(f"**Platforms:** {', '.join(platforms.keys())}")
            
            # Start collection with progress tracking
            with st.container():
                downloaded_files = st.session_state.collector.collect_images(
                    person_name, platforms, download_folder, max_images
                )
                
                # Display results
                if downloaded_files:
                    st.success(f"🎉 Successfully collected {len(downloaded_files)} images!")
                    
                    # Show downloaded images in columns
                    st.subheader("🖼️ Downloaded Images")
                    cols = st.columns(4)
                    
                    for i, file_path in enumerate(downloaded_files):
                        try:
                            with cols[i % 4]:
                                image = Image.open(file_path)
                                st.image(image, caption=Path(file_path).name, use_column_width=True)
                        except Exception as e:
                            st.write(f"⚠️ Could not display {Path(file_path).name}")
                    
                    # Download summary
                    st.info(f"📁 Images saved to: {download_folder}")
                else:
                    st.error("❌ No images were successfully downloaded. Try different search terms or check platform usernames.")
    
    else:
        # Instructions when not running
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("ℹ️ How to Use")
            st.markdown("""
            ### 🎯 **Search Strategy:**
            1. **GitHub** - API-based, highest quality ✨
            2. **Twitter/X** - Multiple proxy methods 🐦
            3. **LinkedIn** - Professional photos 💼
            4. **Bing Images** - Often better than Google 🔍
            5. **DuckDuckGo** - Privacy-focused search 🦆
            
            ### 📝 **Tips for Best Results:**
            - Use **exact usernames** for platforms
            - Try **full names** with quotes for search
            - **LinkedIn URLs** work best (full profile URL)
            - **GitHub usernames** are most reliable
            """)
        
        with col2:
            st.subheader("🤖 Free AI Integrations")
            st.markdown("""
            ### **Face Enhancement APIs:**
            
            ```python
            # Hugging Face - Face Detection
            API_URL = "https://api-inference.huggingface.co/models/adrienle/face-detection"
            
            # Replicate - Image Upscaling  
            replicate.run("nightmareai/real-esrgan:...")
            
            # DeepAI - Super Resolution
            r = requests.post(
                "https://api.deepai.org/api/torch-srgan",
                files={'image': open('image.jpg', 'rb')},
                headers={'api-key': 'YOUR_API_KEY'}
            )
            ```
            
            **All offer free tiers!** 🆓
            """)
    
    # Footer
    st.markdown("---")
    st.markdown("*Enhanced Profile Image Collector v3.0 | Made with ❤️ using Streamlit*")

if __name__ == "__main__":
    main()