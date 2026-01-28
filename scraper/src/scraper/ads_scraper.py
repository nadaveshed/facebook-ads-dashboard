import logging
import os
import re
import time
import hashlib
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
            driver_path = ChromeDriverManager().install()
            # WebDriver Manager 4.x / Chrome 127+ returns wrong file (THIRD_PARTY_NOTICES.chromedriver)
            # instead of the actual binary. Use the real "chromedriver" in the same directory.
            if driver_path and os.path.exists(driver_path):
                if os.path.isdir(driver_path):
                    driver_path = os.path.join(driver_path, 'chromedriver')
                else:
                    parent = os.path.dirname(driver_path)
                    # Binary is named exactly "chromedriver"; WDM often returns THIRD_PARTY_NOTICES.chromedriver
                    if os.path.basename(driver_path) != 'chromedriver':
                        candidate = os.path.join(parent, 'chromedriver')
                        if os.path.isfile(candidate):
                            driver_path = candidate
                if os.path.isfile(driver_path):
                    os.chmod(driver_path, 0o755)
            service = Service(driver_path)
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

            # Try to dismiss cookie/login overlays that hide the actual ad content
            try:
                self._dismiss_overlays()
            except Exception:
                pass

            # Wait a bit for dynamic ad content to appear (Library ID / creative container)
            try:
                WebDriverWait(self.driver, 10).until(
                    lambda d: len(
                        d.find_elements(
                            By.CSS_SELECTOR, '[data-testid="ad-library-dynamic-content-container"]'
                        )
                    )
                    > 0
                    or len(d.find_elements(By.XPATH, "//*[contains(normalize-space(.), 'Library ID:')]"))
                    > 0
                )
            except TimeoutException:
                logger.warning("Ad content did not fully appear yet; continuing anyway")
            
            logger.info("Successfully navigated to Ads Library")
            return True
            
        except TimeoutException:
            logger.error("Timeout while navigating to Ads Library")
            return False

    def _dismiss_overlays(self) -> None:
        """Best-effort close cookie consent/login overlays so ads render normally."""
        if not self.driver:
            return
        # Common consent buttons (varies by region/language)
        candidates = [
            "Allow all cookies",
            "Accept all cookies",
            "Accept All",
            "Allow all",
            "Only allow essential cookies",
            "Reject optional cookies",
            "Reject all",
        ]
        for label in candidates:
            try:
                buttons = self.driver.find_elements(
                    By.XPATH, f"//div[@role='button' and contains(normalize-space(.), '{label}')]"
                )
                if buttons:
                    buttons[0].click()
                    time.sleep(0.5)
                    break
            except Exception:
                continue

        # Close dialog "X" buttons (best-effort)
        try:
            close_buttons = self.driver.find_elements(
                By.XPATH, "//div[@role='button' and (@aria-label='Close' or @aria-label='close')]"
            )
            if close_buttons:
                close_buttons[0].click()
                time.sleep(0.2)
        except Exception:
            pass
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return False
    
    def _scroll_to_load_ads(self, target_count: int) -> None:
        logger.info(f"Scrolling to load {target_count} ads...")
        last_count = 0
        scroll_attempts = 0
        max_attempts = 50

        def _count_cards() -> int:
            # The Ads Library renders each ad inside this container in the live DOM.
            try:
                containers = self.driver.find_elements(
                    By.CSS_SELECTOR, '[data-testid="ad-library-dynamic-content-container"]'
                )
                if containers:
                    return len(containers)
            except Exception:
                pass
            # Fallback: older/alternate structures
            try:
                ad_elements = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="ad_card"]')
                if not ad_elements:
                    ad_elements = self.driver.find_elements(By.CSS_SELECTOR, '[role="article"]')
                return len(ad_elements)
            except Exception:
                return 0

        while scroll_attempts < max_attempts:
            try:
                current_count = _count_cards()
            except NoSuchElementException:
                current_count = 0

            if current_count >= target_count:
                logger.info(f"Reached target: {current_count} ads loaded")
                last_count = current_count
                break

            if current_count == last_count:
                scroll_attempts += 1
            else:
                scroll_attempts = 0
                last_count = current_count

            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(self.config.scraper.scroll_delay_ms / 1000.0)

        logger.info(f"Finished scrolling. Total ads found: {last_count}")

    def _get_ad_card_elements(self, max_ads: int) -> List[Any]:
        """Get ad card elements that actually contain ad text/media."""
        cards: List[Any] = []
        seen_lib_ids: set[str] = set()
        seen_element_ids: set[str] = set()

        def _extract_lib_id_from_element(el) -> Optional[str]:
            """Find the Library ID span inside the element without calling full .text."""
            try:
                spans = el.find_elements(By.XPATH, ".//span[contains(., 'Library ID:')]")
                for s in spans:
                    t = (s.get_attribute("textContent") or "").strip()
                    m = re.search(r'Library\s*ID\s*:\s*([0-9]{10,20})', t, re.IGNORECASE)
                    if m:
                        return m.group(1)
            except Exception:
                pass
            return None

        def _pick_card_from_leaf(leaf) -> Optional[Any]:
            """Walk up from a known leaf element to the full card container."""
            parent = leaf
            best = None
            for _ in range(14):
                try:
                    if parent.get_attribute('data-testid') == 'ad_card':
                        return parent
                    if parent.get_attribute('role') == 'article':
                        best = parent
                    # If this parent contains a Library ID span, it's likely the right card
                    if _extract_lib_id_from_element(parent):
                        best = parent
                except Exception:
                    pass
                try:
                    parent = parent.find_element(By.XPATH, '..')
                except NoSuchElementException:
                    break
            return best

        # Preferred: dynamic content containers (wrap the actual creative/text)
        try:
            containers = self.driver.find_elements(
                By.CSS_SELECTOR, '[data-testid="ad-library-dynamic-content-container"]'
            )
            for c in containers:
                if len(cards) >= max_ads:
                    break
                card = _pick_card_from_leaf(c) or c
                lib_id = _extract_lib_id_from_element(card) or _extract_lib_id_from_element(c)
                eid = getattr(card, 'id', None) or id(card)
                if str(eid) in seen_element_ids:
                    continue
                seen_element_ids.add(str(eid))
                # Dedup by Library ID when available, but do not require it (some cards load it lazily)
                if lib_id:
                    if lib_id in seen_lib_ids:
                        continue
                    seen_lib_ids.add(lib_id)
                cards.append(card)
        except Exception as e:
            logger.debug(f"Dynamic-container card discovery failed: {e}")

        # Fallback: cards by explicit wrapper
        if not cards:
            try:
                wrappers = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="ad_card"]')
                for w in wrappers[:max_ads]:
                    lib_id = _extract_lib_id_from_element(w)
                    if lib_id and lib_id in seen_lib_ids:
                        continue
                    if lib_id:
                        seen_lib_ids.add(lib_id)
                    cards.append(w)
            except Exception:
                pass

        # Last fallback: original selectors
        if not cards:
            try:
                ad_elements = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="ad_card"]')
                if not ad_elements:
                    ad_elements = self.driver.find_elements(By.CSS_SELECTOR, '[role="article"]')
                cards = ad_elements[:max_ads]
            except Exception:
                cards = []

        logger.info(f"Using {len(cards)} ad cards")
        return cards[:max_ads]

    def _extract_main_asset(self, ad_element) -> tuple:
        """Extract the main ad creative (image or video), not icons/avatars.
        Picks the largest image/video in the card to avoid profile pics and icons.
        """
        asset_url = None
        asset_type = AssetType.NONE
        min_creative_size = 120  # ignore icons/avatars smaller than this

        try:
            # Prefer video if present (video ads)
            videos = ad_element.find_elements(By.TAG_NAME, 'video')
            for v in videos:
                src = v.get_attribute('src')
                if not src:
                    try:
                        source = v.find_element(By.TAG_NAME, 'source')
                        src = source.get_attribute('src')
                    except NoSuchElementException:
                        pass
                if src and src.startswith(('http://', 'https://')):
                    return (src, AssetType.VIDEO)

            # Find all images and pick the main creative (largest)
            imgs = ad_element.find_elements(By.TAG_NAME, 'img')
            best_url = None
            best_area = 0
            first_valid_url = None  # fallback if dimensions not loaded (lazy load)

            for img in imgs:
                # Try common lazy-loading attributes + srcset (Meta uses these a lot)
                url = (
                    img.get_attribute('src')
                    or img.get_attribute('data-src')
                    or img.get_attribute('data-original')
                    or img.get_attribute('data-lazy-src')
                )
                srcset = img.get_attribute('srcset')
                if (not url or not url.startswith(('http://', 'https://', '//'))) and srcset:
                    try:
                        # Take the last (usually largest) candidate in srcset
                        parts = [p.strip() for p in srcset.split(',') if p.strip()]
                        if parts:
                            last = parts[-1]
                            url = last.split(' ')[0].strip()
                    except Exception:
                        pass

                if not url:
                    continue
                if url.startswith('//'):
                    url = f'https:{url}'
                if not url.startswith(('http://', 'https://')):
                    continue

                if first_valid_url is None:
                    first_valid_url = url
                # Skip tiny or placeholder images (icons, avatars) - pick largest
                width, height = 0, 0
                try:
                    # Prefer natural dimensions (actual image size); fallback to element size
                    w = img.get_attribute('naturalWidth') or img.get_attribute('width')
                    h = img.get_attribute('naturalHeight') or img.get_attribute('height')
                    if w is not None and h is not None:
                        try:
                            w_str = re.sub(r'[^0-9]', '', str(w))
                            h_str = re.sub(r'[^0-9]', '', str(h))
                            width = int(w_str) if w_str else 0
                            height = int(h_str) if h_str else 0
                        except (ValueError, TypeError):
                            width, height = 0, 0
                    if (width or height) == 0 and self.driver:
                        try:
                            dims = self.driver.execute_script(
                                "var i = arguments[0]; return [i.naturalWidth || i.width || 0, i.naturalHeight || i.height || 0];",
                                img
                            )
                            if dims and len(dims) == 2:
                                width, height = int(dims[0]) or 0, int(dims[1]) or 0
                        except Exception:
                            pass
                    if (width or height) == 0 and img.size:
                        width = img.size.get('width', 0) or 0
                        height = img.size.get('height', 0) or 0
                    if width < min_creative_size and height < min_creative_size:
                        continue
                    area = width * height
                    if area > best_area:
                        best_area = area
                        best_url = url
                except Exception:
                    if best_url is None:
                        best_url = url
                        best_area = 1

            if best_url:
                return (best_url, AssetType.IMAGE)
            # No large image found (e.g. dimensions not loaded yet) - use first valid URL
            if first_valid_url:
                return (first_valid_url, AssetType.IMAGE)

            # Fallback: background-image URLs (some ad creatives are rendered this way)
            try:
                style = ad_element.get_attribute('style') or ''
                m = re.search(r'url\([\"\\\']?(https?://[^)\"\\\']+)', style)
                if m:
                    return (m.group(1), AssetType.IMAGE)
            except Exception:
                pass

            # Fallback: scan outerHTML for image URLs (Meta often uses lazy src, data-src, or inline styles)
            try:
                outer = ad_element.get_attribute('outerHTML') or ''
                # Match src="https://...", data-src="...", url(https://...) - prefer fbcdn/scontent image hosts
                url_pattern = r'(?:src|data-src|data-original)\s*=\s*["\'](https?://[^"\']+)["\']|url\(\s*["\']?(https?://[^)"\']+)["\']?\s*\)'
                for m in re.finditer(url_pattern, outer):
                    url = (m.group(1) or m.group(2) or '').strip()
                    if not url or url.startswith('blob:'):
                        continue
                    if any(x in url for x in ('fbcdn.net', 'scontent.', 'cdninstagram', '.jpg', '.jpeg', '.png', '.webp')):
                        if 'emoji' not in url.lower() and 'avatar' not in url.lower() and 'icon' not in url.lower():
                            return (url.split('"')[0].split("'")[0], AssetType.IMAGE)
            except Exception:
                pass
        except Exception as e:
            logger.debug(f"Asset extraction failed: {e}")

        return (asset_url, asset_type)

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
                        elif pattern == patterns[1]:
                            # e.g. "Nov 8, 2023"
                            try:
                                return datetime.strptime(match.group(0), '%b %d, %Y').date()
                            except ValueError:
                                try:
                                    return datetime.strptime(match.group(0), '%B %d, %Y').date()
                                except ValueError:
                                    continue
                        elif pattern == patterns[2]:
                            return date(int(groups[0]), int(groups[1]), int(groups[2]))
                except ValueError:
                    continue
        
        return None

    def _extract_date_range(self, text: str) -> tuple[Optional[date], Optional[date]]:
        """Extract date range like 'Nov 8, 2023 - Apr 26, 2025' or 'Nov 8, 2023 - Present'."""
        if not text:
            return (None, None)
        # Common single-date format in Ads Library
        # Example: "Started running on Aug 15, 2023"
        m = re.search(
            r'Started\s+running\s+on\s+([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})',
            text,
            re.IGNORECASE,
        )
        if m:
            start = self._parse_date(m.group(1))
            return (start, None)

        m = re.search(
            r'([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})\s*-\s*(Present|[A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})',
            text,
        )
        if not m:
            return (None, None)
        start = self._parse_date(m.group(1))
        end = None if m.group(2).lower() == 'present' else self._parse_date(m.group(2))
        return (start, end)
    
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

    def _extract_platforms_from_dom(self, ad_element) -> List[Platform]:
        """Try to extract platforms from aria-label/title in the card DOM."""
        found: set[Platform] = set()
        try:
            labeled = ad_element.find_elements(By.XPATH, ".//*[@aria-label or @title]")
            for el in labeled:
                val = (el.get_attribute("aria-label") or el.get_attribute("title") or "").lower()
                if not val:
                    continue
                if "facebook" in val:
                    found.add(Platform.FACEBOOK)
                if "instagram" in val:
                    found.add(Platform.INSTAGRAM)
                if "messenger" in val:
                    found.add(Platform.MESSENGER)
                if "audience network" in val or "audience_network" in val:
                    found.add(Platform.AUDIENCE_NETWORK)
        except Exception:
            pass
        return list(found)

    def _extract_primary_text(self, scope) -> Optional[str]:
        """Best-effort extract the main ad copy (the sentence above the creative).

        We intentionally filter out common UI labels like "Library ID", "Platforms", etc.
        """
        if not scope:
            return None

        def _clean(s: str) -> str:
            s = (s or '').replace('\u200b', '').replace('\ufeff', '')
            # Preserve spaces but normalize
            s = re.sub(r'\s+', ' ', s or '').strip()
            return s

        def _strip_common_prefixes(s: str) -> str:
            # Many cards concatenate brand + "Sponsored" into the textContent
            s = re.sub(r'^\s*Nike\s*Sponsored\s*', '', s, flags=re.IGNORECASE)
            s = re.sub(r'^\s*NikeSponsored\s*', '', s, flags=re.IGNORECASE)
            return s.strip()

        blacklist = re.compile(
            r'(Library\s*ID\s*:|ActiveLibrary\s*ID\s*:|Platforms?|Started\s+running\s+on|This\s+ad\s+has\s+multiple\s+versions|EU\s+transparency|See\s+ad\s+details|Open\s+Dropdown)',
            re.IGNORECASE,
        )

        # 1) Strong signal: the primary text is usually rendered in a block with
        #    style "white-space: pre-wrap" (this is the text ABOVE the image).
        try:
            prewrap_nodes = scope.find_elements(
                By.XPATH,
                ".//*[contains(@style,'white-space: pre-wrap')]//span[normalize-space()] | .//*[contains(@style,'white-space: pre-wrap')][normalize-space()]",
            )
            for n in prewrap_nodes:
                try:
                    t_raw = (n.get_attribute('textContent') or n.text or '') or ''
                    t = _strip_common_prefixes(_clean(t_raw))
                    if not t:
                        continue
                    if len(t) < 10 or len(t) > 600:
                        continue
                    if blacklist.search(t):
                        continue
                    return t
                except Exception:
                    continue
        except Exception:
            pass

        candidates: list[str] = []
        try:
            # Scan smaller text nodes first (spans/divs). This is more likely to capture the "primary text".
            nodes = scope.find_elements(By.XPATH, ".//div[normalize-space()] | .//span[normalize-space()]")
            for n in nodes:
                try:
                    t = _strip_common_prefixes(_clean((n.get_attribute('textContent') or n.text or '') or ''))
                    if not t:
                        continue
                    if len(t) < 20:
                        continue
                    if len(t) > 400:
                        continue
                    if blacklist.search(t):
                        continue
                    # Avoid "link preview" / CTA blocks that are often duplicated across many ads
                    # Example user reported: "Get the gear... NIKE.COM Nike Air Monarch IV ... Shop Now"
                    if 'shop now' in t.lower() and 'nike.com' in t.lower() and len(t) > 120:
                        continue
                    # Avoid strings that are basically just numbers/IDs
                    if re.fullmatch(r'[0-9\s\-_:]+', t):
                        continue
                    candidates.append(t)
                except Exception:
                    continue
        except Exception:
            pass

        if not candidates:
            return None

        # Prefer "sentence-like" candidates: has punctuation/line-ish text, then length
        def _score(s: str) -> tuple[int, int]:
            sentenceish = 1 if re.search(r'[.!?]|\\b(and|but|porque|y|que)\\b', s, re.IGNORECASE) else 0
            return (sentenceish, len(s))

        candidates.sort(key=_score, reverse=True)
        return candidates[0]
    
    # Regex for Facebook Ads Library numeric ID (typically 15-16 digits, e.g. 3859568210970246)
    _LIBRARY_ID_NUMERIC = re.compile(r'[0-9]{10,20}')

    def _extract_lib_id_from_element(self, element) -> Optional[str]:
        """Extract Library ID only from this element's subtree (no parents).
        Use this to tie lib_id to the same DOM node as the creative (container).
        """
        if not element:
            return None
        try:
            # data attributes on this element only
            for attr in ('data-ad-id', 'data-adarchive-id', 'data-id'):
                val = element.get_attribute(attr)
                if val and self._LIBRARY_ID_NUMERIC.fullmatch(str(val).strip()):
                    return val.strip()
            # links inside this element only (ads/library?id=...)
            for link in element.find_elements(By.TAG_NAME, 'a'):
                href = (link.get_attribute('href') or '').strip()
                if 'ads/library' in href:
                    m = re.search(r'[?&]id=([0-9]{10,20})', href)
                    if m:
                        return m.group(1)
            # outerHTML of this element only
            outer = element.get_attribute('outerHTML') or ""
            m = re.search(r'Library\s*ID\s*:\s*([0-9]{10,20})', outer, re.IGNORECASE)
            if m:
                return m.group(1)
            m = re.search(r'["\']?id["\']?\s*[:=]\s*["\']?([0-9]{10,20})["\']?', outer, re.IGNORECASE)
            if m:
                return m.group(1)
            m = re.search(r'[?&]id=([0-9]{10,20})', outer)
            if m:
                return m.group(1)
            # visible text inside this element only
            text = (element.get_attribute('textContent') or element.text or "") or ""
            for pattern in [
                r'\b(?:Ad|Library)\s*ID\s*[:\s]+([0-9]{10,20})',
                r'\bID\s*[:\s]+([0-9]{10,20})',
                r'#([0-9]{10,20})',
            ]:
                m = re.search(pattern, text, re.IGNORECASE)
                if m:
                    return m.group(1)
        except Exception:
            pass
        return None

    def _extract_ad_data(self, ad_element) -> Optional[Dict[str, Any]]:
        try:
            ad_id = None
            lib_id = None
            ad_text = (ad_element.get_attribute('textContent') or ad_element.text or "") or ""

            # Method 1: data-ad-id (or similar) on element and parents
            for attr in ('data-ad-id', 'data-adarchive-id', 'data-id'):
                ad_id = ad_element.get_attribute(attr)
                if ad_id and self._LIBRARY_ID_NUMERIC.fullmatch(ad_id.strip()):
                    break
                ad_id = None
            if not ad_id and self.driver:
                try:
                    parent = ad_element
                    for _ in range(4):
                        if parent is None:
                            break
                        for attr in ('data-ad-id', 'data-adarchive-id', 'data-id'):
                            val = parent.get_attribute(attr)
                            if val and self._LIBRARY_ID_NUMERIC.fullmatch(str(val).strip()):
                                ad_id = val.strip()
                                break
                        if ad_id:
                            break
                        try:
                            parent = parent.find_element(By.XPATH, '..')
                        except NoSuchElementException:
                            parent = None
                except Exception:
                    pass

            # Method 2: Links to Ads Library with id= (e.g. .../ads/library/?id=3859568210970246)
            if not ad_id:
                try:
                    links = ad_element.find_elements(By.TAG_NAME, 'a')
                    for link in links:
                        href = (link.get_attribute('href') or '').strip()
                        if 'ads/library' in href:
                            m = re.search(r'[?&]id=([0-9]{10,20})', href)
                            if m:
                                ad_id = m.group(1)
                                break
                except Exception:
                    pass

            # Method 3: Any 10-20 digit id= in the card HTML (data attributes, JSON, etc.)
            if not ad_id:
                outer = ad_element.get_attribute('outerHTML') or ""
                # Direct "Library ID: 123..." present in HTML text nodes
                m = re.search(r'Library\s*ID\s*:\s*([0-9]{10,20})', outer, re.IGNORECASE)
                if m:
                    ad_id = m.group(1)
                m = re.search(r'["\']?id["\']?\s*[:=]\s*["\']?([0-9]{10,20})["\']?', outer, re.IGNORECASE)
                if m:
                    ad_id = m.group(1)
                if not ad_id:
                    m = re.search(r'[?&]id=([0-9]{10,20})', outer)
                    if m:
                        ad_id = m.group(1)

            # Method 4: Visible text "Ad ID: 123..." / "Library ID: 123..."
            if not ad_id:
                patterns = [
                    r'\b(?:Ad|Library)\s*ID\s*[:\s]+([0-9]{10,20})',
                    r'\bID\s*[:\s]+([0-9]{10,20})',
                    r'#([0-9]{10,20})',
                ]
                for pattern in patterns:
                    m = re.search(pattern, ad_text, re.IGNORECASE)
                    if m:
                        ad_id = m.group(1)
                        break

            # Method 5: Fallback - hash of outerHTML for uniqueness (only when no numeric ID found)
            if not ad_id:
                outer = ad_element.get_attribute('outerHTML') or ""
                outer_hash = hashlib.md5(outer.encode('utf-8', errors='ignore')).hexdigest()[:12]
                ad_id = f"lib_{outer_hash}"

            # lib_id is the numeric Library ID (prefer numeric; fallback to ad_id if needed)
            lib_id = ad_id
            logger.debug(f"Extracted Library ID: {lib_id} (ad_id: {ad_id})")
            
            # Detect status from DOM elements (more reliable than text parsing)
            status = AdStatus.INACTIVE  # Default to inactive
            try:
                # Look for status badge/indicator in the card - Facebook uses specific classes/attributes
                # Check for "Active" or "Inactive" text in spans/divs
                status_elements = ad_element.find_elements(By.XPATH, ".//span[contains(., 'Active') or contains(., 'Inactive')] | .//div[contains(., 'Active') or contains(., 'Inactive')]")
                for elem in status_elements:
                    elem_text = (elem.text or "").strip()
                    # Check if this element specifically contains status (not just part of other text)
                    if re.search(r'^Active$|^Inactive$', elem_text, re.IGNORECASE):
                        if re.search(r'^Active$', elem_text, re.IGNORECASE):
                            status = AdStatus.ACTIVE
                            break
                        elif re.search(r'^Inactive$', elem_text, re.IGNORECASE):
                            status = AdStatus.INACTIVE
                            break
                    # Also check for "Active" or "Inactive" as standalone words
                    elif re.search(r'\bActive\b', elem_text, re.IGNORECASE) and not re.search(r'\bInactive\b', elem_text, re.IGNORECASE):
                        status = AdStatus.ACTIVE
                        break
                    elif re.search(r'\bInactive\b', elem_text, re.IGNORECASE):
                        status = AdStatus.INACTIVE
                        break
            except Exception:
                pass
            
            # Fallback to text parsing if DOM search didn't find status
            if status == AdStatus.INACTIVE:
                # Check if text explicitly says "Active" (not just "Inactive")
                if re.search(r'\bActive\b', ad_text, re.IGNORECASE) and not re.search(r'\bInactive\b', ad_text, re.IGNORECASE):
                    status = AdStatus.ACTIVE
            
            start_date, end_date = self._extract_date_range(ad_text)
            
            platforms = self._extract_platforms(ad_text)
            dom_platforms = self._extract_platforms_from_dom(ad_element)
            if dom_platforms:
                merged = {p for p in platforms}
                merged.update(dom_platforms)
                platforms = list(merged)
            
            # Prefer extracting creative from the dynamic content container when present
            asset_scope = ad_element
            try:
                asset_scope = ad_element.find_element(By.CSS_SELECTOR, '[data-testid="ad-library-dynamic-content-container"]')
            except Exception:
                pass
            asset_url, asset_type = self._extract_main_asset(asset_scope)
            
            primary_text = self._extract_primary_text(ad_element)
            return {
                'ad_id': ad_id,
                'lib_id': lib_id,
                # Store plain strings for DB (psycopg2 can't adapt Enum objects)
                'status': status.value,
                'platforms': [p.value for p in platforms],
                'start_date': start_date,
                'end_date': end_date,
                'asset_url': asset_url,
                'asset_type': asset_type.value,
                'ad_content': sanitize_text((primary_text or ad_text)[:500])
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

                # The Ads Library list is virtualized; scrape while scrolling and collecting unique cards.
                self._scroll_to_load_ads(max_ads)
                time.sleep(1.0)

                collected: Dict[str, Dict[str, Any]] = {}
                seen_hashes: set[str] = set()
                scroll_attempts = 0
                max_scroll_attempts = 40
                last_collected = 0

                while len(collected) < max_ads and scroll_attempts < max_scroll_attempts:
                    try:
                        containers = self.driver.find_elements(
                            By.CSS_SELECTOR, '[data-testid="ad-library-dynamic-content-container"]'
                        )
                    except Exception:
                        containers = []

                    for container in containers:
                        if len(collected) >= max_ads:
                            break
                        try:
                            outer = container.get_attribute('outerHTML') or ""
                            h = hashlib.md5(outer.encode('utf-8', errors='ignore')).hexdigest()[:12]
                            if h in seen_hashes:
                                continue
                            seen_hashes.add(h)

                            # Ensure card is rendered (lazy load)
                            try:
                                self.driver.execute_script(
                                    "arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});",
                                    container,
                                )
                                time.sleep(0.8)
                            except Exception:
                                pass

                            # Prefer the full card wrapper around this container
                            card = container
                            try:
                                card = container.find_element(By.XPATH, "ancestor::*[@data-testid='ad_card'][1]")
                            except Exception:
                                try:
                                    card = container.find_element(By.XPATH, "ancestor::*[@role='article'][1]")
                                except Exception:
                                    card = container

                            # New association strategy:
                            # pick the *smallest* ancestor scope that contains EXACTLY:
                            # - 1 creative container
                            # - 1 "Library ID: <numeric>" span
                            lib_id_numeric = None
                            metadata_scope = None
                            try:
                                current = container
                                for _ in range(14):
                                    try:
                                        containers_in_scope = current.find_elements(
                                            By.CSS_SELECTOR,
                                            '[data-testid="ad-library-dynamic-content-container"]',
                                        )
                                        lib_spans = current.find_elements(By.XPATH, ".//span[contains(., 'Library ID:')]")
                                        ids: set[str] = set()
                                        for s in lib_spans:
                                            t = (s.get_attribute('textContent') or s.text or '') or ''
                                            m = re.search(r'Library\s*ID\s*:\s*([0-9]{10,20})', t, re.IGNORECASE)
                                            if m:
                                                ids.add(m.group(1))
                                        if len(containers_in_scope) == 1 and len(ids) == 1:
                                            lib_id_numeric = next(iter(ids))
                                            metadata_scope = current
                                            break
                                    except Exception:
                                        pass
                                    try:
                                        current = current.find_element(By.XPATH, "..")
                                    except NoSuchElementException:
                                        break
                            except Exception:
                                pass

                            if not lib_id_numeric:
                                # Fallback: best-effort extract from the card (may be less precise)
                                lib_id_numeric = self._extract_lib_id_from_element(card)
                                metadata_scope = card

                            if not lib_id_numeric:
                                logger.warning("Skipping container: no numeric Library ID found")
                                continue

                            ad_data = self._extract_ad_data(metadata_scope or card)
                            if not ad_data:
                                continue

                            # Overwrite with the numeric lib_id we found
                            ad_data['lib_id'] = lib_id_numeric
                            ad_data['ad_id'] = lib_id_numeric

                            # Extract asset from THIS container only (avoid mixing another ad's image)
                            asset_url, asset_type = self._extract_main_asset(container)
                            ad_data['asset_url'] = asset_url
                            ad_data['asset_type'] = asset_type.value

                            asset_url = ad_data.get('asset_url')
                            if asset_url:
                                if asset_url.startswith('blob:'):
                                    logger.warning(
                                        f"Ad ({ad_data['ad_id']}): blob URL cannot be downloaded, skipping"
                                    )
                                else:
                                    filename, _ = download_asset(
                                        asset_url,
                                        self.config.scraper.assets_dir,
                                        ad_data.get('lib_id') or ad_data['ad_id'],
                                    )
                                    if filename:
                                        ad_data['asset_path'] = filename
                                    else:
                                        logger.warning(
                                            f"Ad ({ad_data['ad_id']}): download failed"
                                        )
                            else:
                                logger.info(
                                    f"Ad ({ad_data['ad_id']}): no image/video URL found in ad card"
                                )

                            key = ad_data.get('lib_id') or ad_data.get('ad_id')
                            if key:
                                if key not in collected:
                                    collected[key] = ad_data
                                else:
                                    # Do NOT overwrite an existing creative/text with another "version"
                                    # (Ads Library often shows "This ad has multiple versions" under the same Library ID).
                                    # Only fill missing fields.
                                    existing = collected[key]
                                    for field in ('status', 'platforms', 'start_date', 'end_date', 'asset_type', 'asset_url', 'asset_path', 'ad_content'):
                                        if existing.get(field) in (None, '', [], {}):
                                            if ad_data.get(field) not in (None, '', [], {}):
                                                existing[field] = ad_data.get(field)
                                    collected[key] = existing
                        except Exception:
                            continue

                    if len(collected) == last_collected:
                        scroll_attempts += 1
                    else:
                        scroll_attempts = 0
                        last_collected = len(collected)

                    # Scroll further to load more virtualized cards
                    try:
                        self.driver.execute_script("window.scrollBy(0, window.innerHeight * 1.2);")
                    except Exception:
                        pass
                    time.sleep(self.config.scraper.scroll_delay_ms / 1000.0)

                ads = list(collected.values())
                logger.info(f"Collected {len(ads)} unique ads from the page")
                
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
