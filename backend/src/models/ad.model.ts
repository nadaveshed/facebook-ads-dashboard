export interface Ad {
    id: number;
    ad_id: string;
    lib_id: string;
    status: 'active' | 'inactive';
    platforms: string[];
    start_date: string | null;
    end_date: string | null;
    asset_type: 'image' | 'video' | 'none';
    asset_url: string | null;
    asset_path: string | null;
    ad_content: string | null;
    advertiser_name: string;
    created_at: string;
    updated_at: string;
}

export interface AdFilters {
    status?: 'active' | 'inactive';
    platform?: string;
    startDate?: string;
    endDate?: string;
}

export interface AdStats {
    totalAds: number;
    activeAds: number;
    inactiveAds: number;
    adsOverTime: {
        date: string;
        active: number;
        inactive: number;
        total: number;
    }[];
    platformDistribution: {
        platform: string;
        count: number;
    }[];
}

export interface PaginatedResponse<T> {
    data: T[];
    total: number;
    page: number;
    pageSize: number;
    totalPages: number;
}
