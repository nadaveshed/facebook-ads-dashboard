import logging
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

from .config import get_config
from .database import DatabaseConnection, AdRepository
from .scraper import FacebookAdsScraper


def wait_for_database(max_retries: int = 30, delay: int = 2) -> DatabaseConnection:
    db = DatabaseConnection()
    
    for attempt in range(max_retries):
        try:
            db.connect()
            logger.info("Successfully connected to database")
            return db
        except Exception as e:
            logger.warning(f"Database connection attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(delay)
    
    raise RuntimeError("Failed to connect to database after maximum retries")


def run_scraper() -> int:
    config = get_config()
    
    logger.info("Connecting to database...")
    db = wait_for_database()
    repo = AdRepository(db)
    
    try:
        logger.info("Starting Facebook Ads Library scraper...")
        scraper = FacebookAdsScraper()
        ads = scraper.scrape_ads(config.scraper.max_ads)
        logger.info(f"Scraped {len(ads)} ads from Facebook")
        
        if ads:
            count = repo.insert_ads_batch(ads)
            logger.info(f"Stored {count} ads in database")
            return count
        
        return 0
        
    finally:
        db.disconnect()


def main():
    logger.info("=" * 50)
    logger.info("Facebook Ads Scraper Starting")
    logger.info("=" * 50)
    
    try:
        count = run_scraper()
        logger.info(f"Scraper completed successfully. Total ads: {count}")
        return 0
    except Exception as e:
        logger.error(f"Scraper failed with error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
