CREATE TABLE IF NOT EXISTS ads (
    id SERIAL PRIMARY KEY,
    ad_id VARCHAR(255) UNIQUE NOT NULL,
    lib_id VARCHAR(255) UNIQUE,
    status VARCHAR(50) NOT NULL CHECK (status IN ('active', 'inactive')),
    platforms TEXT[] NOT NULL DEFAULT '{}',
    start_date DATE,
    end_date DATE,
    asset_type VARCHAR(50) CHECK (asset_type IN ('image', 'video', 'none')),
    asset_url TEXT,
    asset_path VARCHAR(500),
    ad_content TEXT,
    advertiser_name VARCHAR(255) DEFAULT 'Nike',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_ads_status ON ads(status);
CREATE INDEX idx_ads_start_date ON ads(start_date);
CREATE INDEX idx_ads_end_date ON ads(end_date);
CREATE INDEX idx_ads_platforms ON ads USING GIN(platforms);
