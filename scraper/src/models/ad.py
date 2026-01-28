from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional
from enum import Enum


class AdStatus(Enum):
    ACTIVE = 'active'
    INACTIVE = 'inactive'


class AssetType(Enum):
    IMAGE = 'image'
    VIDEO = 'video'
    NONE = 'none'


class Platform(Enum):
    FACEBOOK = 'facebook'
    INSTAGRAM = 'instagram'
    MESSENGER = 'messenger'
    AUDIENCE_NETWORK = 'audience_network'


@dataclass
class Ad:
    ad_id: str
    status: AdStatus
    platforms: List[Platform]
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    asset_type: AssetType = AssetType.NONE
    asset_path: Optional[str] = None
    ad_content: Optional[str] = None
    advertiser_name: str = 'Nike'
    
    def to_dict(self) -> dict:
        return {
            'ad_id': self.ad_id,
            'status': self.status.value,
            'platforms': [p.value for p in self.platforms],
            'start_date': self.start_date,
            'end_date': self.end_date,
            'asset_type': self.asset_type.value,
            'asset_path': self.asset_path,
            'ad_content': self.ad_content,
            'advertiser_name': self.advertiser_name
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Ad':
        return cls(
            ad_id=data['ad_id'],
            status=AdStatus(data['status']),
            platforms=[Platform(p) for p in data.get('platforms', [])],
            start_date=data.get('start_date'),
            end_date=data.get('end_date'),
            asset_type=AssetType(data.get('asset_type', 'none')),
            asset_path=data.get('asset_path'),
            ad_content=data.get('ad_content'),
            advertiser_name=data.get('advertiser_name', 'Nike')
        )
