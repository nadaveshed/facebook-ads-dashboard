import logging
import re
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

from ..config import get_config
from ..models import Ad, AdStatus, AssetType, Platform
from ..utils import download_asset, sanitize_text

logger = logging.getLogger(__name__)


class FacebookAdsScraper:
    
    def __init__(self):
        self.config = get_config()
        self.driver: Optional[webdriver.Chrome] = None
    
    def _start_browser(self) -> None:
        logger.info("Starting Chrome browser with Selenium...")
        
        chrome_options = Options()
        if self.config.scraper.headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.set_page_load_timeout(60)
            logger.info("Chrome browser started successfully")
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            raise
    
    def _stop_browser(self) -> None:
        if self.driver:
            self.driver.quit()
            logger.info("Browser stopped")
    
    def _navigate_to_ads_library(self) -> bool:
        try:
            logger.info(f"Navigating to: {self.config.scraper.target_url}")
            self.driver.get(self.config.scraper.target_url)
            
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            try:
                WebDriverWait(self.driver, 10).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "body > *"))
                )
            except TimeoutException:
                logger.warning("Page took longer than expected to load, continuing anyway")
            
            logger.info("Successfully navigated to Ads Library")
            return True
            
        except TimeoutException:
            logger.error("Timeout while navigating to Ads Library")
            return False
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return False
    
    def _scroll_to_load_ads(self, target_count: int) -> None:
        logger.info(f"Scrolling to load {target_count} ads...")
        last_count = 0
        scroll_attempts = 0
        max_attempts = 50
        
        import time
        
        while scroll_attempts < max_attempts:
            try:
                ad_elements = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="ad_card"]')
                if not ad_elements:
                    ad_elements = self.driver.find_elements(By.CSS_SELECTOR, '.x1yztbdb')
                if not ad_elements:
                    ad_elements = self.driver.find_elements(By.CSS_SELECTOR, '[role="article"]')
            except NoSuchElementException:
                ad_elements = []
            
            current_count = len(ad_elements)
            
            if current_count >= target_count:
                logger.info(f"Reached target: {current_count} ads loaded")
                break
            
            if current_count == last_count:
                scroll_attempts += 1
            else:
                scroll_attempts = 0
                last_count = current_count
            
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(self.config.scraper.scroll_delay_ms / 1000.0)
        
        logger.info(f"Finished scrolling. Total ads found: {last_count}")
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        if not date_str:
            return None
        
        patterns = [
            r'(\d{1,2})/(\d{1,2})/(\d{4})',
            r'(\w+)\s+(\d{1,2}),\s+(\d{4})',
            r'(\d{4})-(\d{2})-(\d{2})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, date_str)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 3:
                        if pattern == patterns[0]:
                            return date(int(groups[2]), int(groups[0]), int(groups[1]))
                        elif pattern == patterns[2]:
                            return date(int(groups[0]), int(groups[1]), int(groups[2]))
                except ValueError:
                    continue
        
        return None
    
    def _extract_platforms(self, text: str) -> List[Platform]:
        platforms = []
        text_lower = text.lower()
        
        if 'facebook' in text_lower:
            platforms.append(Platform.FACEBOOK)
        if 'instagram' in text_lower:
            platforms.append(Platform.INSTAGRAM)
        if 'messenger' in text_lower:
            platforms.append(Platform.MESSENGER)
        if 'audience network' in text_lower:
            platforms.append(Platform.AUDIENCE_NETWORK)
        
        if not platforms:
            platforms.append(Platform.FACEBOOK)
        
        return platforms
    
    def _extract_ad_data(self, ad_element) -> Optional[Dict[str, Any]]:
        try:
            ad_id = ad_element.get_attribute('data-ad-id')
            if not ad_id:
                content = ad_element.text[:100]
                ad_id = f"ad_{abs(hash(content)) % 10000000000}"
            
            ad_text = ad_element.text
            
            status = AdStatus.ACTIVE if 'Active' in ad_text else AdStatus.INACTIVE
            
            start_date = self._parse_date(ad_text)
            end_date = None
            
            if 'ended' in ad_text.lower() or 'inactive' in ad_text.lower():
                status = AdStatus.INACTIVE
                match = re.search(r'ended.*?(\d+/\d+/\d+)', ad_text.lower())
                if match:
                    end_date = self._parse_date(match.group(1))
            
            platforms = self._extract_platforms(ad_text)
            
            asset_url = None
            asset_type = AssetType.NONE
            
            try:
                img_element = ad_element.find_element(By.TAG_NAME, 'img')
                if img_element:
                    asset_url = img_element.get_attribute('src')
                    asset_type = AssetType.IMAGE
            except NoSuchElementException:
                pass
            
            try:
                video_element = ad_element.find_element(By.TAG_NAME, 'video')
                if video_element:
                    asset_url = video_element.get_attribute('src')
                    asset_type = AssetType.VIDEO
            except NoSuchElementException:
                pass
            
            return {
                'ad_id': ad_id,
                'status': status,
                'platforms': platforms,
                'start_date': start_date,
                'end_date': end_date,
                'asset_url': asset_url,
                'asset_type': asset_type,
                'ad_content': sanitize_text(ad_text[:500])
            }
            
        except Exception as e:
            logger.error(f"Failed to extract ad data: {e}")
            return None
    
    def scrape_ads(self, max_ads: Optional[int] = None, max_retries: int = 3) -> List[Dict[str, Any]]:
        max_ads = max_ads or self.config.scraper.max_ads
        ads = []
        
        for attempt in range(max_retries):
            try:
                self._start_browser()
                
                if not self._navigate_to_ads_library():
                    logger.error("Failed to navigate to Ads Library")
                    if attempt < max_retries - 1:
                        logger.info(f"Retrying... (attempt {attempt + 2}/{max_retries})")
                        self._stop_browser()
                        continue
                    return ads
                
                self._scroll_to_load_ads(max_ads)
                
                ad_elements = []
                try:
                    ad_elements = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="ad_card"]')
                    if not ad_elements:
                        ad_elements = self.driver.find_elements(By.CSS_SELECTOR, '.x1yztbdb')
                    if not ad_elements:
                        ad_elements = self.driver.find_elements(By.CSS_SELECTOR, '[role="article"]')
                except Exception as e:
                    logger.error(f"Failed to find ad elements: {e}")
                    if attempt < max_retries - 1:
                        logger.info(f"Retrying... (attempt {attempt + 2}/{max_retries})")
                        self._stop_browser()
                        continue
                    break
                
                logger.info(f"Found {len(ad_elements)} ad elements")
                
                for i, element in enumerate(ad_elements[:max_ads]):
                    ad_data = self._extract_ad_data(element)
                    if ad_data:
                        if ad_data.get('asset_url'):
                            filename, _ = download_asset(
                                ad_data['asset_url'],
                                self.config.scraper.assets_dir,
                                ad_data['ad_id']
                            )
                            if filename:
                                ad_data['asset_path'] = filename
                        
                        ads.append(ad_data)
                        logger.info(f"Scraped ad {i+1}/{max_ads}: {ad_data['ad_id']}")
                
                break
                
            except Exception as e:
                logger.error(f"Scraping failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying... (attempt {attempt + 2}/{max_retries})")
                    self._stop_browser()
                else:
                    logger.error("Max retries reached, giving up")
            finally:
                self._stop_browser()
        
        return ads
    
    def __enter__(self):
        self._start_browser()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._stop_browser()
        return False
