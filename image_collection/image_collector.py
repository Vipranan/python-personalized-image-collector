import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import requests
import os
import time
import threading
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import json
from typing import List, Dict, Optional
import hashlib
from PIL import Image, ImageTk
import io

class ProfileImageScraperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Profile Image Scraper")
        self.root.geometry("800x700")
        self.root.configure(bg='#f0f0f0')
        
        # Initialize scraper session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        self.download_folder = "profile_images"
        self.is_scraping = False
        
        self.create_widgets()
    
    def create_widgets(self):
        # Title
        title_label = tk.Label(self.root, text="Profile Image Scraper", 
                              font=('Arial', 20, 'bold'), bg='#f0f0f0', fg='#333')
        title_label.pack(pady=10)
        
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Person name input
        name_frame = ttk.Frame(main_frame)
        name_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(name_frame, text="Person Name:", font=('Arial', 12, 'bold')).pack(anchor=tk.W)
        self.name_entry = ttk.Entry(name_frame, font=('Arial', 11), width=50)
        self.name_entry.pack(fill=tk.X, pady=(5, 0))
        
        # Platforms frame
        platforms_frame = ttk.LabelFrame(main_frame, text="Platform Usernames (Optional)", padding="10")
        platforms_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Twitter
        twitter_frame = ttk.Frame(platforms_frame)
        twitter_frame.pack(fill=tk.X, pady=2)
        ttk.Label(twitter_frame, text="Twitter/X:", width=12).pack(side=tk.LEFT)
        self.twitter_entry = ttk.Entry(twitter_frame, width=30)
        self.twitter_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        # GitHub
        github_frame = ttk.Frame(platforms_frame)
        github_frame.pack(fill=tk.X, pady=2)
        ttk.Label(github_frame, text="GitHub:", width=12).pack(side=tk.LEFT)
        self.github_entry = ttk.Entry(github_frame, width=30)
        self.github_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        # LinkedIn
        linkedin_frame = ttk.Frame(platforms_frame)
        linkedin_frame.pack(fill=tk.X, pady=2)
        ttk.Label(linkedin_frame, text="LinkedIn URL:", width=12).pack(side=tk.LEFT)
        self.linkedin_entry = ttk.Entry(linkedin_frame, width=40)
        self.linkedin_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        # Settings frame
        settings_frame = ttk.LabelFrame(main_frame, text="Settings", padding="10")
        settings_frame.pack(fill=tk.X, pady=(0, 15))
        
        folder_frame = ttk.Frame(settings_frame)
        folder_frame.pack(fill=tk.X, pady=2)
        ttk.Label(folder_frame, text="Download Folder:", width=15).pack(side=tk.LEFT)
        self.folder_var = tk.StringVar(value=self.download_folder)
        self.folder_entry = ttk.Entry(folder_frame, textvariable=self.folder_var, width=35)
        self.folder_entry.pack(side=tk.LEFT, padx=(5, 5))
        ttk.Button(folder_frame, text="Browse", command=self.browse_folder).pack(side=tk.LEFT)
        
        # Max images setting
        max_frame = ttk.Frame(settings_frame)
        max_frame.pack(fill=tk.X, pady=2)
        ttk.Label(max_frame, text="Max Images:", width=15).pack(side=tk.LEFT)
        self.max_images_var = tk.StringVar(value="10")
        ttk.Entry(max_frame, textvariable=self.max_images_var, width=10).pack(side=tk.LEFT, padx=(5, 0))
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.start_button = ttk.Button(buttons_frame, text="Start Scraping", 
                                      command=self.start_scraping, style='Accent.TButton')
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = ttk.Button(buttons_frame, text="Stop", 
                                     command=self.stop_scraping, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(buttons_frame, text="Clear Log", command=self.clear_log).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(buttons_frame, text="Open Folder", command=self.open_download_folder).pack(side=tk.LEFT)
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=(0, 10))
        
        # Log area
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, font=('Consolas', 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def log_message(self, message):
        """Add message to log area"""
        self.log_text.insert(tk.END, f"{time.strftime('%H:%M:%S')} - {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def clear_log(self):
        """Clear the log area"""
        self.log_text.delete(1.0, tk.END)
    
    def browse_folder(self):
        """Browse for download folder"""
        folder = filedialog.askdirectory(initialdir=self.folder_var.get())
        if folder:
            self.folder_var.set(folder)
            self.download_folder = folder
    
    def open_download_folder(self):
        """Open the download folder in file explorer"""
        if os.path.exists(self.download_folder):
            if os.name == 'nt':  # Windows
                os.startfile(self.download_folder)
            elif os.name == 'posix':  # macOS and Linux
                os.system(f'open "{self.download_folder}"')
        else:
            messagebox.showwarning("Folder Not Found", f"Folder '{self.download_folder}' does not exist.")
    
    def start_scraping(self):
        """Start the scraping process"""
        person_name = self.name_entry.get().strip()
        if not person_name:
            messagebox.showerror("Error", "Please enter a person name.")
            return
        
        self.is_scraping = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.progress.start()
        self.status_var.set("Scraping in progress...")
        
        # Start scraping in a separate thread
        self.scraping_thread = threading.Thread(target=self.scrape_images, args=(person_name,))
        self.scraping_thread.daemon = True
        self.scraping_thread.start()
    
    def stop_scraping(self):
        """Stop the scraping process"""
        self.is_scraping = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.progress.stop()
        self.status_var.set("Scraping stopped")
        self.log_message("Scraping stopped by user")
    
    def scrape_images(self, person_name):
        """Main scraping method (runs in separate thread)"""
        try:
            self.download_folder = self.folder_var.get()
            os.makedirs(self.download_folder, exist_ok=True)
            
            # Collect platform info
            platforms = {}
            if self.twitter_entry.get().strip():
                platforms['twitter'] = self.twitter_entry.get().strip()
            if self.github_entry.get().strip():
                platforms['github'] = self.github_entry.get().strip()
            if self.linkedin_entry.get().strip():
                platforms['linkedin'] = self.linkedin_entry.get().strip()
            
            max_images = int(self.max_images_var.get() or 10)
            
            self.log_message(f"Starting scrape for: {person_name}")
            self.log_message(f"Max images: {max_images}")
            
            all_images = []
            
            # Check specific platforms
            for platform, username in platforms.items():
                if not self.is_scraping:
                    break
                
                self.log_message(f"Checking {platform}: {username}")
                
                if platform == 'twitter':
                    img = self.scrape_twitter_profile(username)
                elif platform == 'github':
                    img = self.scrape_github_profile(username)
                elif platform == 'linkedin':
                    img = self.scrape_linkedin_profile(username)
                
                if img:
                    all_images.append(img)
                    self.log_message(f"Found image from {platform}")
                
                time.sleep(1)  # Rate limiting
            
            # Search Google Images
            if self.is_scraping and len(all_images) < max_images:
                self.log_message("Searching Google Images...")
                google_images = self.search_google_images(person_name, max_images - len(all_images))
                all_images.extend(google_images)
                self.log_message(f"Found {len(google_images)} images from Google")
            
            # Search alternative sources if needed
            if self.is_scraping and len(all_images) < max_images:
                self.log_message("Searching alternative sources...")
                alt_images = self.search_alternative_sources(person_name, max_images - len(all_images))
                all_images.extend(alt_images)
                self.log_message(f"Found {len(alt_images)} images from alternative sources")
            
            # Validate and filter images
            valid_images = []
            for img in all_images:
                if not self.is_scraping:
                    break
                if self.validate_image_url(img['url']):
                    valid_images.append(img)
                    self.log_message(f"✓ Valid image from {img['source']}")
                else:
                    self.log_message(f"✗ Invalid/inaccessible image from {img['source']}")
            
            # Download images
            downloaded_count = 0
            for i, img_info in enumerate(valid_images[:max_images]):
                if not self.is_scraping:
                    break
                
                if img_info.get('url'):
                    self.log_message(f"Downloading image {i+1}/{len(valid_images)} from {img_info['source']}")
                    filepath = self.download_image(img_info, person_name)
                    if filepath:
                        downloaded_count += 1
                        self.log_message(f"✓ Downloaded: {os.path.basename(filepath)}")
                    else:
                        self.log_message(f"✗ Failed to download from {img_info['source']}")
            
            if self.is_scraping:
                self.log_message(f"Scraping completed! Downloaded {downloaded_count} images.")
                self.status_var.set(f"Completed - {downloaded_count} images downloaded")
                messagebox.showinfo("Complete", f"Successfully downloaded {downloaded_count} images!")
            
        except Exception as e:
            self.log_message(f"Error during scraping: {str(e)}")
            messagebox.showerror("Error", f"An error occurred: {str(e)}")
        
        finally:
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.progress.stop()
            if self.is_scraping:
                self.status_var.set("Ready")
    
    def search_alternative_sources(self, person_name: str, max_results: int = 3) -> List[Dict]:
        """Search alternative sources for images when Google fails"""
        images = []
        
        try:
            # Method 1: DuckDuckGo Images (more lenient than Google)
            self.log_message("Trying DuckDuckGo Images...")
            ddg_url = f"https://duckduckgo.com/?q={person_name.replace(' ', '+')}+profile&iax=images&ia=images"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = self.session.get(ddg_url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for image data in script tags
                scripts = soup.find_all('script')
                for script in scripts:
                    if script.string and 'vqd' in str(script.string):
                        # DuckDuckGo uses vqd tokens, try to extract image URLs
                        import re
                        urls = re.findall(r'https://[^"\']*\.(?:jpg|jpeg|png|gif)', str(script.string))
                        for url in urls[:max_results]:
                            if url not in [img['url'] for img in images]:
                                images.append({
                                    'url': url,
                                    'source': 'DuckDuckGo',
                                    'method': 'alternative_search'
                                })
                                if len(images) >= max_results:
                                    break
            
            time.sleep(1)
            
            # Method 2: Try Bing Images
            if len(images) < max_results and self.is_scraping:
                self.log_message("Trying Bing Images...")
                bing_url = f"https://www.bing.com/images/search?q={person_name.replace(' ', '+')}+profile"
                
                response = self.session.get(bing_url, headers=headers, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Bing uses different structure
                    img_containers = soup.find_all('a', class_='iusc')
                    for container in img_containers[:max_results]:
                        if len(images) >= max_results:
                            break
                        
                        # Bing stores image data in 'm' attribute as JSON
                        m_data = container.get('m')
                        if m_data:
                            try:
                                import json
                                img_data = json.loads(m_data)
                                img_url = img_data.get('murl')
                                if img_url and img_url not in [img['url'] for img in images]:
                                    images.append({
                                        'url': img_url,
                                        'source': 'Bing Images',
                                        'title': img_data.get('t', ''),
                                        'method': 'bing_search'
                                    })
                            except:
                                continue
                
                time.sleep(1)
                
        except Exception as e:
            self.log_message(f"Error in alternative search: {e}")
        
        return images
    
    def validate_image_url(self, url: str) -> bool:
        """Validate if URL is likely to be a real image"""
        try:
            # Quick HEAD request to check if URL exists and is an image
            response = self.session.head(url, timeout=5)
            content_type = response.headers.get('content-type', '').lower()
            
            # Check if it's an image
            if any(img_type in content_type for img_type in ['image/', 'jpeg', 'jpg', 'png', 'gif', 'webp']):
                # Check content length (avoid tiny images)
                content_length = response.headers.get('content-length')
                if content_length and int(content_length) > 1000:  # At least 1KB
                    return True
                elif not content_length:  # Some servers don't send content-length
                    return True
            
        except:
            pass
        
        return False
    
    def search_google_images(self, person_name: str, max_results: int = 5) -> List[Dict]:
        """Search Google Images for profile pictures using multiple methods"""
        images = []
        try:
            # Method 1: Try different search variations
            search_queries = [
                f"{person_name.replace(' ', '+')}+profile+picture",
                f"{person_name.replace(' ', '+')}+headshot",
                f"{person_name.replace(' ', '+')}+photo",
                f'"{person_name}"+image'
            ]
            
            for query in search_queries[:2]:  # Limit to avoid too many requests
                if not self.is_scraping or len(images) >= max_results:
                    break
                    
                search_url = f"https://www.google.com/search?q={query}&tbm=isch&safe=off"
                
                # Try with different headers
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                }
                
                response = self.session.get(search_url, headers=headers, timeout=15)
                self.log_message(f"Google search response status: {response.status_code}")
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Method 1: Look for JSON data in script tags (Google's new format)
                    script_tags = soup.find_all('script')
                    for script in script_tags:
                        if script.string and 'data:image' not in str(script.string):
                            script_content = str(script.string)
                            # Look for image URLs in the JavaScript
                            if 'https://' in script_content and ('jpg' in script_content or 'png' in script_content or 'jpeg' in script_content):
                                import re
                                # Find URLs that look like images
                                url_pattern = r'https://[^"\s]+\.(?:jpg|jpeg|png|gif|webp)'
                                found_urls = re.findall(url_pattern, script_content, re.IGNORECASE)
                                
                                for url in found_urls[:max_results]:
                                    if len(images) >= max_results:
                                        break
                                    if url not in [img['url'] for img in images]:
                                        images.append({
                                            'url': url,
                                            'source': 'Google Images (Script)',
                                            'query': query,
                                            'method': 'script_extraction'
                                        })
                    
                    # Method 2: Traditional img tag search (fallback)
                    img_tags = soup.find_all('img')
                    for img in img_tags:
                        if len(images) >= max_results:
                            break
                        
                        src = img.get('src') or img.get('data-src') or img.get('data-iurl')
                        if src and src.startswith('http') and not src.startswith('data:'):
                            # Filter out small/logo images
                            if not any(skip in src.lower() for skip in ['logo', 'icon', 'button', 'banner']):
                                images.append({
                                    'url': src,
                                    'source': 'Google Images (IMG)',
                                    'alt': img.get('alt', ''),
                                    'method': 'img_tag'
                                })
                
                time.sleep(2)  # Respectful delay between requests
                
        except Exception as e:
            self.log_message(f"Error searching Google Images: {e}")
        
        # Remove duplicates
        unique_images = []
        seen_urls = set()
        for img in images:
            if img['url'] not in seen_urls:
                seen_urls.add(img['url'])
                unique_images.append(img)
        
        return unique_images[:max_results]
    
    def scrape_github_profile(self, username: str) -> Optional[Dict]:
        """Get GitHub profile image"""
        try:
            api_url = f"https://api.github.com/users/{username}"
            response = self.session.get(api_url, timeout=10)
            
            if response.status_code == 200:
                user_data = response.json()
                return {
                    'url': user_data.get('avatar_url'),
                    'source': 'GitHub',
                    'username': username,
                    'name': user_data.get('name', '')
                }
        except Exception as e:
            self.log_message(f"Error fetching GitHub profile: {e}")
        
        return None
    
    def scrape_twitter_profile(self, username: str) -> Optional[Dict]:
        """Attempt to get Twitter profile image using multiple methods"""
        try:
            # Method 1: Try Twitter web page
            url = f"https://twitter.com/{username}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            response = self.session.get(url, headers=headers, timeout=10)
            self.log_message(f"Twitter response status for {username}: {response.status_code}")
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Method 1: Look for og:image meta tag
                og_image = soup.find('meta', property='og:image')
                if og_image and og_image.get('content'):
                    img_url = og_image.get('content')
                    # Make sure it's a high-quality image, not the default
                    if 'default_profile' not in img_url and 'twimg.com' in img_url:
                        return {
                            'url': img_url,
                            'source': 'Twitter/X',
                            'username': username,
                            'method': 'og_image'
                        }
                
                # Method 2: Look for profile image in the page content
                # Twitter sometimes uses different selectors
                img_selectors = [
                    'img[src*="profile_images"]',
                    'img[data-testid="ProfileAvatar-image"]',
                    'div[data-testid="UserAvatar-Container-"] img'
                ]
                
                for selector in img_selectors:
                    profile_img = soup.select_one(selector)
                    if profile_img and profile_img.get('src'):
                        img_url = profile_img.get('src')
                        if 'profile_images' in img_url:
                            # Convert to higher quality version
                            img_url = img_url.replace('_normal', '_400x400')
                            return {
                                'url': img_url,
                                'source': 'Twitter/X',
                                'username': username,
                                'method': 'profile_img_tag'
                            }
            
            # Method 2: Try alternative Twitter URL formats
            alt_url = f"https://x.com/{username}"
            response = self.session.get(alt_url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                og_image = soup.find('meta', property='og:image')
                if og_image and og_image.get('content'):
                    img_url = og_image.get('content')
                    if 'default_profile' not in img_url:
                        return {
                            'url': img_url,
                            'source': 'X.com',
                            'username': username,
                            'method': 'x_com_fallback'
                        }
                        
        except Exception as e:
            self.log_message(f"Error scraping Twitter: {e}")
        
        return None
    
    def scrape_linkedin_profile(self, profile_url: str) -> Optional[Dict]:
        """Attempt to get LinkedIn profile image"""
        try:
            response = self.session.get(profile_url, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                og_image = soup.find('meta', property='og:image')
                if og_image:
                    return {
                        'url': og_image.get('content'),
                        'source': 'LinkedIn',
                        'profile_url': profile_url
                    }
        except Exception as e:
            self.log_message(f"Error scraping LinkedIn: {e}")
        
        return None
    
    def download_image(self, image_info: Dict, person_name: str) -> Optional[str]:
        """Download an image and save it locally"""
        try:
            response = self.session.get(image_info['url'], stream=True, timeout=15)
            response.raise_for_status()
            
            # Generate filename
            url_hash = hashlib.md5(image_info['url'].encode()).hexdigest()[:8]
            source = image_info['source'].replace('/', '_').replace(' ', '_')
            person_folder = os.path.join(self.download_folder, person_name.replace(' ', '_'))
            os.makedirs(person_folder, exist_ok=True)
            
            # Determine file extension
            content_type = response.headers.get('content-type', '')
            if 'jpeg' in content_type or 'jpg' in content_type:
                ext = '.jpg'
            elif 'png' in content_type:
                ext = '.png'
            elif 'gif' in content_type:
                ext = '.gif'
            else:
                ext = '.jpg'
            
            filename = f"{source}_{url_hash}{ext}"
            filepath = os.path.join(person_folder, filename)
            
            # Download and save
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if not self.is_scraping:
                        break
                    f.write(chunk)
            
            return filepath
            
        except Exception as e:
            self.log_message(f"Error downloading image: {e}")
            return None

def main():
    root = tk.Tk()
    app = ProfileImageScraperGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()