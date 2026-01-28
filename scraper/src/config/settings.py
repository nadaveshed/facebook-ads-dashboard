import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class DatabaseConfig:
    url: str
    
    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        return cls(
            url=os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/ads_db')
        )


@dataclass
class ScraperConfig:
    target_url: str
    max_ads: int
    scroll_delay_ms: int
    headless: bool
    assets_dir: str
    
    @classmethod
    def from_env(cls) -> 'ScraperConfig':
        return cls(
            target_url=os.getenv(
                'TARGET_URL',
                'https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=US&is_targeted_country=false&media_type=all&search_type=page&view_all_page_id=15087023444'
            ),
            max_ads=int(os.getenv('MAX_ADS', '50')),
            scroll_delay_ms=int(os.getenv('SCROLL_DELAY_MS', '2000')),
            headless=os.getenv('HEADLESS', 'true').lower() == 'true',
            assets_dir=os.getenv('ASSETS_DIR', './assets')
        )


@dataclass
class AppConfig:
    database: DatabaseConfig
    scraper: ScraperConfig
    
    @classmethod
    def from_env(cls) -> 'AppConfig':
        return cls(
            database=DatabaseConfig.from_env(),
            scraper=ScraperConfig.from_env()
        )


config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    global config
    if config is None:
        config = AppConfig.from_env()
    return config
