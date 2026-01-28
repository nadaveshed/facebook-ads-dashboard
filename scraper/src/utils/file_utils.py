import os
import requests
import logging
import hashlib
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def ensure_directory(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)
    

def get_file_extension(url: str, content_type: Optional[str] = None) -> str:
    parsed = urlparse(url)
    path = parsed.path
    if '.' in path:
        ext = os.path.splitext(path)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.webm', '.mov']:
            return ext
    
    if content_type:
        mime_to_ext = {
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/webp': '.webp',
            'video/mp4': '.mp4',
            'video/webm': '.webm',
            'video/quicktime': '.mov'
        }
        return mime_to_ext.get(content_type.split(';')[0].strip(), '.bin')
    
    return '.bin'


def generate_asset_filename(ad_id: str, url: str, extension: str) -> str:
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    return f"{ad_id}_{url_hash}{extension}"


def download_asset(
    url: str,
    destination_dir: str,
    ad_id: str,
    timeout: int = 30,
    skip_if_exists: bool = True,
) -> Tuple[Optional[str], Optional[str]]:
    """Download asset from URL. If skip_if_exists is True, return existing filename when
    the file we would write already exists (same ad_id + url → same filename)."""
    if not url:
        return None, None

    try:
        ensure_directory(destination_dir)
        extension = get_file_extension(url, None)
        filename = generate_asset_filename(ad_id, url, extension)
        filepath = os.path.join(destination_dir, filename)

        if skip_if_exists and os.path.isfile(filepath):
            asset_type = 'video' if extension in ['.mp4', '.webm', '.mov'] else 'image'
            logger.debug(f"Asset already exists, skipping download: {filename}")
            return filename, asset_type

        response = requests.get(url, timeout=timeout, stream=True)
        response.raise_for_status()

        # Keep same extension (from URL) so skip-if-exists matches on next run
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        asset_type = 'video' if extension in ['.mp4', '.webm', '.mov'] else 'image'

        logger.info(f"Downloaded asset: {filename}")
        return filename, asset_type

    except requests.RequestException as e:
        logger.error(f"Failed to download asset from {url}: {e}")
        return None, None
    except IOError as e:
        logger.error(f"Failed to save asset: {e}")
        return None, None


def sanitize_text(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    text = text.replace('\x00', '')
    text = ' '.join(text.split())
    return text[:5000]
