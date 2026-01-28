import { and, count, desc, eq, gte, lte, or, isNull, sql } from 'drizzle-orm';
import { getDb } from '../database/db';
import { ads } from '../database/schema';
import { Ad, AdFilters, AdStats, PaginatedResponse } from '../models';
import { DatabaseError } from '../errors/AppError';

function toModel(row: typeof ads.$inferSelect): Ad {
    const dateToString = (date: Date | string | null): string | null => {
        if (!date) return null;
        if (typeof date === 'string') return date.split('T')[0];
        if (date instanceof Date) return date.toISOString().split('T')[0];
        return null;
    };

    const dateToISOString = (date: Date | string | null): string => {
        if (!date) return new Date().toISOString();
        if (typeof date === 'string') return date;
        if (date instanceof Date) return date.toISOString();
        return new Date().toISOString();
    };

    return {
        id: row.id,
        ad_id: row.adId,
        status: row.status as 'active' | 'inactive',
        platforms: row.platforms,
        start_date: dateToString(row.startDate),
        end_date: dateToString(row.endDate),
        asset_type: row.assetType as 'image' | 'video' | 'none',
        asset_path: row.assetPath,
        ad_content: row.adContent,
        advertiser_name: row.advertiserName ?? 'Nike',
        created_at: dateToISOString(row.createdAt),
        updated_at: dateToISOString(row.updatedAt),
    };
}

function buildWhereConditions(filters: AdFilters) {
    const conditions = [];
    if (filters.status) {
        conditions.push(eq(ads.status, filters.status));
    }
    if (filters.platform) {
        conditions.push(sql`${filters.platform} = ANY(${ads.platforms})`);
    }
    if (filters.startDate) {
        conditions.push(gte(ads.startDate, filters.startDate));
    }
    if (filters.endDate) {
        conditions.push(or(lte(ads.startDate, filters.endDate), isNull(ads.startDate))!);
    }
    return conditions.length > 0 ? and(...conditions) : undefined;
}

async function getAds(
    filters: AdFilters = {},
    page: number = 1,
    pageSize: number = 20
): Promise<PaginatedResponse<Ad>> {
    try {
        const db = getDb();
        const whereClause = buildWhereConditions(filters);

        const [{ value: total }] = await db
            .select({ value: count() })
            .from(ads)
            .where(whereClause);

        const offset = (page - 1) * pageSize;
        const rows = await db
            .select()
            .from(ads)
            .where(whereClause)
            .orderBy(desc(ads.startDate), ads.id)
            .limit(pageSize)
            .offset(offset);

        const data = rows.map((row: typeof ads.$inferSelect) => toModel(row));

        return {
            data,
            total: Number(total),
            page,
            pageSize,
            totalPages: Math.ceil(Number(total) / pageSize),
        };
    } catch (error) {
        throw new DatabaseError(
            `Failed to fetch ads: ${error instanceof Error ? error.message : 'Unknown error'}`
        );
    }
}

async function getAdById(id: number): Promise<Ad | null> {
    try {
        const db = getDb();
        const [row] = await db.select().from(ads).where(eq(ads.id, id)).limit(1);
        return row ? toModel(row) : null;
    } catch (error) {
        throw new DatabaseError(
            `Failed to fetch ad: ${error instanceof Error ? error.message : 'Unknown error'}`
        );
    }
}

async function getStats(filters: AdFilters = {}): Promise<AdStats> {
    try {
        const db = getDb();
        const whereClause = buildWhereConditions(filters);

        const [totalResult] = await db
            .select({ value: count() })
            .from(ads)
            .where(whereClause);
        const totalAds = Number(totalResult?.value ?? 0);

        const [activeResult] = await db
            .select({ value: count() })
            .from(ads)
            .where(and(whereClause, eq(ads.status, 'active')));
        const activeAds = Number(activeResult?.value ?? 0);

        const [inactiveResult] = await db
            .select({ value: count() })
            .from(ads)
            .where(and(whereClause, eq(ads.status, 'inactive')));
        const inactiveAds = Number(inactiveResult?.value ?? 0);

        const timeData = await db
            .select({
                date: sql<string>`TO_CHAR(${ads.startDate}, 'YYYY-MM')`,
                active: sql<string>`COUNT(*) FILTER (WHERE ${ads.status} = 'active')`,
                inactive: sql<string>`COUNT(*) FILTER (WHERE ${ads.status} = 'inactive')`,
                total: sql<string>`COUNT(*)`,
            })
            .from(ads)
            .where(and(whereClause, sql`${ads.startDate} IS NOT NULL`))
            .groupBy(sql`TO_CHAR(${ads.startDate}, 'YYYY-MM')`)
            .orderBy(sql`TO_CHAR(${ads.startDate}, 'YYYY-MM')`);

        const platformConditions: ReturnType<typeof sql>[] = [];
        if (filters.startDate) {
            platformConditions.push(sql`start_date >= ${filters.startDate}`);
        }
        if (filters.endDate) {
            platformConditions.push(sql`start_date <= ${filters.endDate}`);
        }
        if (filters.platform) {
            platformConditions.push(sql`${filters.platform} = ANY(platforms)`);
        }
        const platformWhere =
            platformConditions.length > 0
                ? sql`WHERE ${sql.join(platformConditions, sql` AND `)}`
                : sql``;

        const platformResult = await db.execute<{ platform: string; count: string }>(
            sql`SELECT platform, COUNT(*)::text as count FROM ads, UNNEST(platforms) as platform ${platformWhere} GROUP BY platform ORDER BY count DESC`
        );
        const platformRows = 'rows' in platformResult ? platformResult.rows : [];

        return {
            totalAds,
            activeAds,
            inactiveAds,
            adsOverTime: timeData.map(
                (row: { date: string; active: string; inactive: string; total: string }) => ({
                    date: row.date,
                    active: parseInt(row.active, 10),
                    inactive: parseInt(row.inactive, 10),
                    total: parseInt(row.total, 10),
                })
            ),
            platformDistribution: (platformRows as { platform: string; count: string }[]).map(
                (row) => ({
                    platform: row.platform,
                    count: parseInt(row.count, 10),
                })
            ),
        };
    } catch (error) {
        throw new DatabaseError(
            `Failed to fetch stats: ${error instanceof Error ? error.message : 'Unknown error'}`
        );
    }
}

export const adService = {
    getAds,
    getAdById,
    getStats,
};
