import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from typing import List, Optional, Dict, Any
from contextlib import contextmanager
import logging

from ..config import get_config

logger = logging.getLogger(__name__)


class DatabaseConnection:
    
    def __init__(self):
        self.config = get_config()
        self._connection = None
    
    def connect(self) -> None:
        try:
            self._connection = psycopg2.connect(self.config.database.url)
            self._connection.autocommit = False
            logger.info("Successfully connected to database")
        except psycopg2.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def disconnect(self) -> None:
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("Disconnected from database")
    
    @contextmanager
    def get_cursor(self):
        if not self._connection:
            self.connect()
        cursor = self._connection.cursor(cursor_factory=RealDictCursor)
        try:
            yield cursor
            self._connection.commit()
        except Exception as e:
            self._connection.rollback()
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            cursor.close()


class AdRepository:
    
    def __init__(self, db: DatabaseConnection):
        self.db = db
    
    def insert_ad(self, ad_data: Dict[str, Any]) -> int:
        with self.db.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO ads (ad_id, lib_id, status, platforms, start_date, end_date,
                                asset_type, asset_url, asset_path, ad_content, advertiser_name)
                VALUES (%(ad_id)s, %(lib_id)s, %(status)s, %(platforms)s, %(start_date)s, %(end_date)s,
                        %(asset_type)s, %(asset_url)s, %(asset_path)s, %(ad_content)s, %(advertiser_name)s)
                ON CONFLICT (ad_id) DO UPDATE SET
                    lib_id = COALESCE(EXCLUDED.lib_id, ads.lib_id),
                    status = EXCLUDED.status,
                    platforms = EXCLUDED.platforms,
                    end_date = EXCLUDED.end_date,
                    asset_type = EXCLUDED.asset_type,
                    asset_url = COALESCE(EXCLUDED.asset_url, ads.asset_url),
                    asset_path = COALESCE(EXCLUDED.asset_path, ads.asset_path),
                    ad_content = EXCLUDED.ad_content,
                    updated_at = NOW()
                RETURNING id
            """, ad_data)
            result = cursor.fetchone()
            return result['id']
    
    def insert_ads_batch(self, ads: List[Dict[str, Any]]) -> int:
        if not ads:
            return 0

        with self.db.get_cursor() as cursor:
            values = [
                (
                    ad['ad_id'],
                    ad.get('lib_id') or ad['ad_id'],
                    ad['status'],
                    ad['platforms'],
                    ad.get('start_date'),
                    ad.get('end_date'),
                    ad.get('asset_type', 'none'),
                    ad.get('asset_url'),
                    ad.get('asset_path'),
                    ad.get('ad_content'),
                    ad.get('advertiser_name', 'Nike'),
                )
                for ad in ads
            ]

            execute_values(
                cursor,
                """
                INSERT INTO ads (ad_id, lib_id, status, platforms, start_date, end_date,
                                asset_type, asset_url, asset_path, ad_content, advertiser_name)
                VALUES %s
                ON CONFLICT (ad_id) DO UPDATE SET
                    lib_id = COALESCE(EXCLUDED.lib_id, ads.lib_id),
                    status = EXCLUDED.status,
                    platforms = EXCLUDED.platforms,
                    end_date = EXCLUDED.end_date,
                    asset_type = EXCLUDED.asset_type,
                    asset_url = COALESCE(EXCLUDED.asset_url, ads.asset_url),
                    asset_path = COALESCE(EXCLUDED.asset_path, ads.asset_path),
                    ad_content = EXCLUDED.ad_content,
                    updated_at = NOW()
                """,
                values,
            )
            return len(ads)
    
    def get_ad_by_id(self, ad_id: str) -> Optional[Dict[str, Any]]:
        with self.db.get_cursor() as cursor:
            cursor.execute("SELECT * FROM ads WHERE ad_id = %s", (ad_id,))
            return cursor.fetchone()
    
    def get_all_ads(self) -> List[Dict[str, Any]]:
        with self.db.get_cursor() as cursor:
            cursor.execute("SELECT * FROM ads ORDER BY start_date DESC")
            return cursor.fetchall()
    
    def count_ads(self) -> int:
        with self.db.get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM ads")
            result = cursor.fetchone()
            return result['count']
