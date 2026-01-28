import {
    pgTable,
    serial,
    varchar,
    text,
    date,
    timestamp,
    index,
} from 'drizzle-orm/pg-core';
import { sql } from 'drizzle-orm';

export const adStatusEnum = ['active', 'inactive'] as const;
export const assetTypeEnum = ['image', 'video', 'none'] as const;
export type AdStatus = (typeof adStatusEnum)[number];
export type AssetType = (typeof assetTypeEnum)[number];

export const ads = pgTable(
    'ads',
    {
        id: serial('id').primaryKey(),
        adId: varchar('ad_id', { length: 255 }).unique().notNull(),
        status: varchar('status', { length: 50 }).notNull(),
        platforms: text('platforms').array().notNull().default(sql`'{}'`),
        startDate: date('start_date'),
        endDate: date('end_date'),
        assetType: varchar('asset_type', { length: 50 }),
        assetPath: varchar('asset_path', { length: 500 }),
        adContent: text('ad_content'),
        advertiserName: varchar('advertiser_name', { length: 255 }).default('Nike'),
        createdAt: timestamp('created_at', { withTimezone: true }).defaultNow(),
        updatedAt: timestamp('updated_at', { withTimezone: true }).defaultNow(),
    },
    (table) => [
        index('idx_ads_status').on(table.status),
        index('idx_ads_start_date').on(table.startDate),
        index('idx_ads_end_date').on(table.endDate),
        index('idx_ads_platforms').on(table.platforms),
    ]
);

export type AdRow = typeof ads.$inferSelect;
export type AdInsert = typeof ads.$inferInsert;
