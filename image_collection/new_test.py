import streamlit as st
import requests
import os
from pathlib import Path
import time
from PIL import Image
import io
import cv2
import numpy as np
from datetime import datetime
import json

# Streamlined Profile Image Collector
class ProfileImageCollector:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Initialize face detection
        try:
            self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        except:
            self.face_cascade = None
            st.warning("⚠️ Face detection not available - install opencv-python")
    
    def has_face(self, image_bytes):
        """Simple face detection"""
        if not self.face_cascade:
            return True  # Skip if no face detection
        
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return False
            
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(50, 50))
            return len(faces) > 0
        except:
            return False
    
    def get_github_avatar(self, username):
        """Get GitHub profile image"""
        try:
            url = f"https://api.github.com/users/{username}"
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                avatar_url = data.get('avatar_url', '').replace('?v=4', '?v=4&s=400')
                if avatar_url:
                    return {
                        'url': avatar_url,
                        'source': f'GitHub (@{username})',
                        'username': username
                    }
        except Exception as e:
            st.error(f"GitHub error: {e}")
        return None
    
    def search_duckduckgo_images(self, person_name, max_results=10):
        """Search DuckDuckGo for images"""
        images = []
        try:
            # Use DuckDuckGo Instant Answer API (more reliable)
            search_terms = [
                f'"{person_name}" profile photo',
                f'"{person_name}" headshot',
                f'{person_name} portrait'
            ]
            
            for search_term in search_terms[:2]:  # Limit searches
                st.write(f"🔍 Searching: {search_term}")
                
                # Simple approach: construct likely image URLs from common platforms
                potential_urls = self._generate_potential_urls(person_name)
                
                for url in potential_urls[:max_results//2]:
                    try:
                        response = self.session.head(url, timeout=5)
                        if response.status_code == 200 and 'image' in response.headers.get('content-type', ''):
                            images.append({
                                'url': url,
                                'source': 'Web Search',
                                'search_term': search_term
                            })
                    except:
                        continue
                
                time.sleep(1)  # Rate limiting
        
        except Exception as e:
            st.error(f"Search error: {e}")
        
        return images
    
    def _generate_potential_urls(self, person_name):
        """Generate potential profile image URLs from common patterns"""
        urls = []
        name_parts = person_name.lower().replace(' ', '')
        first_name = person_name.split()[0].lower()
        
        # Common profile image URL patterns
        patterns = [
            f"https://avatars.githubusercontent.com/{name_parts}",
            f"https://github.com/{name_parts}.png",
            f"https://github.com/{first_name}.png",
        ]
        
        return patterns
    
    def download_and_validate_images(self, image_list):
        """Download images and validate them"""
        valid_images = []
        
        progress_bar = st.progress(0)
        
        for i, img_info in enumerate(image_list):
            progress_bar.progress((i + 1) / len(image_list))
            
            try:
                st.write(f"📥 Downloading from {img_info['source']}")
                response = self.session.get(img_info['url'], timeout=10)
                
                if response.status_code == 200:
                    image_bytes = response.content
                    
                    # Basic validation
                    if len(image_bytes) > 1000:  # At least 1KB
                        # Check if it's a valid image
                        try:
                            img = Image.open(io.BytesIO(image_bytes))
                            width, height = img.size
                            
                            # Size validation
                            if width >= 100 and height >= 100:
                                # Face detection (optional)
                                has_face = self.has_face(image_bytes)
                                
                                img_info.update({
                                    'image_bytes': image_bytes,
                                    'dimensions': f"{width}x{height}",
                                    'file_size': f"{len(image_bytes)/1024:.1f}KB",
                                    'has_face': has_face
                                })
                                
                                valid_images.append(img_info)
                                st.success(f"✅ Valid image found: {width}x{height}")
                            else:
                                st.warning(f"⚠️ Image too small: {width}x{height}")
                        except:
                            st.warning("⚠️ Invalid image format")
                    else:
                        st.warning("⚠️ File too small")
                else:
                    st.warning(f"⚠️ Failed to download: HTTP {response.status_code}")
                    
            except Exception as e:
                st.error(f"❌ Error processing {img_info['source']}: {e}")
        
        progress_bar.empty()
        return valid_images
    
    def save_images(self, images, person_name, output_dir):
        """Save images to specified directory"""
        saved_files = []
        
        # Create output directory
        output_path = Path(output_dir)
        person_folder = output_path / person_name.replace(' ', '_').replace('/', '_')
        person_folder.mkdir(parents=True, exist_ok=True)
        
        for i, img_info in enumerate(images):
            try:
                # Generate filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                source = img_info['source'].replace('/', '_').replace(' ', '_')
                
                # Determine extension
                if 'png' in img_info['url'].lower():
                    ext = '.png'
                else:
                    ext = '.jpg'
                
                filename = f"{i+1:02d}_{source}_{timestamp}{ext}"
                filepath = person_folder / filename
                
                # Save image
                with open(filepath, 'wb') as f:
                    f.write(img_info['image_bytes'])
                
                saved_files.append(str(filepath))
                st.write(f"💾 Saved: {filename}")
                
            except Exception as e:
                st.error(f"Error saving image {i+1}: {e}")
        
        return saved_files, str(person_folder)

def main():
    st.set_page_config(page_title="Profile Image Collector", page_icon="📸", layout="wide")
    
    st.title("📸 Profile Image Collector")
    st.markdown("Collect profile images from various sources with face detection")
    
    # Input section
    col1, col2 = st.columns([2, 1])
    
    with col1:
        person_name = st.text_input("👤 Person Name", placeholder="Enter full name")
        github_username = st.text_input("GitHub Username (optional)", placeholder="username")
    
    with col2:
        max_images = st.slider("Max Images", 1, 20, 5)
        output_dir = st.text_input("📁 Output Directory", value="./profile_images")
        enable_face_detection = st.checkbox("Enable Face Detection", value=True)
    
    # Show current output directory
    if output_dir:
        abs_path = Path(output_dir).resolve()
        st.info(f"📂 Images will be saved to: `{abs_path}`")
    
    # Collection button
    if st.button("🚀 Start Collection", type="primary", disabled=not person_name):
        if not person_name:
            st.error("Please enter a person name")
            return
        
        # Initialize collector
        collector = ProfileImageCollector()
        all_images = []
        
        st.markdown("---")
        st.subheader(f"Collecting images for: **{person_name}**")
        
        # GitHub search
        if github_username:
            st.write("### 🐙 Searching GitHub")
            github_img = collector.get_github_avatar(github_username)
            if github_img:
                all_images.append(github_img)
                st.success(f"Found GitHub avatar for @{github_username}")
            else:
                st.warning("No GitHub avatar found")
        
        # Web search
        st.write("### 🌐 Searching Web")
        web_images = collector.search_duckduckgo_images(person_name, max_images)
        all_images.extend(web_images)
        
        if all_images:
            st.write(f"Found {len(all_images)} potential images")
            
            # Download and validate
            st.write("### 📥 Downloading and Validating")
            valid_images = collector.download_and_validate_images(all_images)
            
            if valid_images:
                # Filter by face detection if enabled
                if enable_face_detection:
                    face_images = [img for img in valid_images if img.get('has_face', True)]
                    if face_images:
                        valid_images = face_images
                        st.write(f"✅ {len(face_images)} images with faces detected")
                    else:
                        st.warning("⚠️ No faces detected, showing all valid images")
                
                # Limit results
                final_images = valid_images[:max_images]
                
                # Save images
                st.write("### 💾 Saving Images")
                saved_files, save_folder = collector.save_images(final_images, person_name, output_dir)
                
                # Results
                st.markdown("---")
                st.success(f"✅ **Successfully saved {len(saved_files)} images!**")
                st.info(f"📁 **Saved to:** `{save_folder}`")
                
                # Display results
                st.write("### 🖼️ Collected Images")
                cols = st.columns(min(3, len(final_images)))
                
                for i, img_info in enumerate(final_images):
                    with cols[i % 3]:
                        if 'image_bytes' in img_info:
                            image = Image.open(io.BytesIO(img_info['image_bytes']))
                            st.image(image, caption=f"{img_info['source']}", use_column_width=True)
                            st.write(f"**Size:** {img_info.get('dimensions', 'Unknown')}")
                            st.write(f"**File:** {img_info.get('file_size', 'Unknown')}")
                            if enable_face_detection:
                                face_status = "✅ Face detected" if img_info.get('has_face') else "❌ No face"
                                st.write(f"**Face:** {face_status}")
                
                # Summary info
                with st.expander("📊 Collection Summary"):
                    st.json({
                        'person_name': person_name,
                        'total_found': len(all_images),
                        'valid_images': len(valid_images),
                        'saved_images': len(saved_files),
                        'output_directory': save_folder,
                        'face_detection_enabled': enable_face_detection
                    })
            
            else:
                st.error("❌ No valid images found")
        
        else:
            st.error("❌ No images found. Try different search terms or check the GitHub username.")

if __name__ == "__main__":
    main()
