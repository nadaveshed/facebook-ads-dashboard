import { AppDataSource } from '../database/data-source';
import { Ad as AdEntity, AdStatus } from '../entities';
import { Ad, AdFilters, AdStats, PaginatedResponse } from '../models';
import { DatabaseError } from '../errors/AppError';
import { Repository } from 'typeorm';

function getAdRepository(): Repository<AdEntity> {
    return AppDataSource.getRepository(AdEntity);
}

function toModel(entity: AdEntity): Ad {
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
        id: entity.id,
        ad_id: entity.ad_id,
        lib_id: entity.lib_id,
        status: entity.status as 'active' | 'inactive',
        platforms: entity.platforms,
        start_date: dateToString(entity.start_date),
        end_date: dateToString(entity.end_date),
        asset_type: entity.asset_type as 'image' | 'video' | 'none',
        asset_url: entity.asset_url,
        asset_path: entity.asset_path,
        ad_content: entity.ad_content,
        advertiser_name: entity.advertiser_name,
        created_at: dateToISOString(entity.created_at),
        updated_at: dateToISOString(entity.updated_at),
    };
}

async function getAds(
    filters: AdFilters = {},
    page: number = 1,
    pageSize: number = 20
): Promise<PaginatedResponse<Ad>> {
    try {
        const adRepository = getAdRepository();
        const queryBuilder = adRepository.createQueryBuilder('ad');

            if (filters.status) {
                queryBuilder.andWhere('ad.status = :status', { status: filters.status });
            }

            if (filters.platform) {
                queryBuilder.andWhere(':platform = ANY(ad.platforms)', { platform: filters.platform });
            }

            if (filters.startDate) {
                queryBuilder.andWhere('ad.start_date >= :startDate', { 
                    startDate: filters.startDate 
                });
            }

            if (filters.endDate) {
                queryBuilder.andWhere(
                    '(ad.start_date <= :endDate OR ad.start_date IS NULL)',
                    { endDate: filters.endDate }
                );
            }

            const total = await queryBuilder.getCount();

            const offset = (page - 1) * pageSize;
            const entities = await queryBuilder
                .orderBy('ad.start_date', 'DESC', 'NULLS LAST')
                .skip(offset)
                .take(pageSize)
                .getMany();

            const data = entities.map(entity => toModel(entity));

            return {
                data,
                total,
                page,
                pageSize,
                totalPages: Math.ceil(total / pageSize),
            };
        } catch (error) {
            throw new DatabaseError(`Failed to fetch ads: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
}

async function getAdById(id: number): Promise<Ad | null> {
    try {
        const adRepository = getAdRepository();
        const entity = await adRepository.findOne({ where: { id } });
        return entity ? toModel(entity) : null;
    } catch (error) {
        throw new DatabaseError(`Failed to fetch ad: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
}

async function getStats(filters: AdFilters = {}): Promise<AdStats> {
    try {
        const adRepository = getAdRepository();
        const queryBuilder = adRepository.createQueryBuilder('ad');

            if (filters.startDate) {
                queryBuilder.andWhere('ad.start_date >= :startDate', { 
                    startDate: filters.startDate 
                });
            }

            if (filters.endDate) {
                queryBuilder.andWhere(
                    '(ad.start_date <= :endDate OR ad.start_date IS NULL)',
                    { endDate: filters.endDate }
                );
            }

            if (filters.platform) {
                queryBuilder.andWhere(':platform = ANY(ad.platforms)', { platform: filters.platform });
            }

            const totalAds = await queryBuilder.getCount();
            
            const activeQuery = adRepository.createQueryBuilder('ad');
            if (filters.startDate) {
                activeQuery.andWhere('ad.start_date >= :startDate', { startDate: filters.startDate });
            }
            if (filters.endDate) {
                activeQuery.andWhere('(ad.start_date <= :endDate OR ad.start_date IS NULL)', { endDate: filters.endDate });
            }
            if (filters.platform) {
                activeQuery.andWhere(':platform = ANY(ad.platforms)', { platform: filters.platform });
            }
            const activeAds = await activeQuery
                .andWhere('ad.status = :status', { status: AdStatus.ACTIVE })
                .getCount();

            const inactiveQuery = adRepository.createQueryBuilder('ad');
            if (filters.startDate) {
                inactiveQuery.andWhere('ad.start_date >= :startDate', { startDate: filters.startDate });
            }
            if (filters.endDate) {
                inactiveQuery.andWhere('(ad.start_date <= :endDate OR ad.start_date IS NULL)', { endDate: filters.endDate });
            }
            if (filters.platform) {
                inactiveQuery.andWhere(':platform = ANY(ad.platforms)', { platform: filters.platform });
            }
            const inactiveAds = await inactiveQuery
                .andWhere('ad.status = :status', { status: AdStatus.INACTIVE })
                .getCount();

            const timeQuery = adRepository
                .createQueryBuilder('ad')
                .select("TO_CHAR(ad.start_date, 'YYYY-MM')", 'date')
                .addSelect("COUNT(*) FILTER (WHERE ad.status = 'active')", 'active')
                .addSelect("COUNT(*) FILTER (WHERE ad.status = 'inactive')", 'inactive')
                .addSelect('COUNT(*)', 'total')
                .where('ad.start_date IS NOT NULL')
                .groupBy("TO_CHAR(ad.start_date, 'YYYY-MM')")
                .orderBy('date', 'ASC');

            if (filters.startDate) {
                timeQuery.andWhere('ad.start_date >= :startDate', { startDate: filters.startDate });
            }

            if (filters.endDate) {
                timeQuery.andWhere('ad.start_date <= :endDate', { endDate: filters.endDate });
            }

            if (filters.platform) {
                timeQuery.andWhere(':platform = ANY(ad.platforms)', { platform: filters.platform });
            }

            const timeData = await timeQuery.getRawMany();

            const platformQuery = adRepository
                .createQueryBuilder('ad')
                .select('platform', 'platform')
                .addSelect('COUNT(*)', 'count')
                .from((subQuery) => {
                    return subQuery
                        .select('ad.id', 'id')
                        .addSelect('UNNEST(ad.platforms)', 'platform')
                        .from(AdEntity, 'ad');
                }, 'platforms')
                .groupBy('platform')
                .orderBy('count', 'DESC');

            const basePlatformQuery = adRepository.createQueryBuilder('ad');
            if (filters.startDate) {
                basePlatformQuery.andWhere('ad.start_date >= :startDate', { startDate: filters.startDate });
            }
            if (filters.endDate) {
                basePlatformQuery.andWhere('ad.start_date <= :endDate', { endDate: filters.endDate });
            }
            if (filters.platform) {
                basePlatformQuery.andWhere(':platform = ANY(ad.platforms)', { platform: filters.platform });
            }

            const platformParams: any[] = [];
            let paramIndex = 1;
            const platformConditions: string[] = [];
            
            if (filters.startDate) {
                platformConditions.push(`start_date >= $${paramIndex++}`);
                platformParams.push(filters.startDate);
            }
            if (filters.endDate) {
                platformConditions.push(`start_date <= $${paramIndex++}`);
                platformParams.push(filters.endDate);
            }
            if (filters.platform) {
                platformConditions.push(`$${paramIndex++} = ANY(platforms)`);
                platformParams.push(filters.platform);
            }
            
            const platformWhere = platformConditions.length > 0 
                ? `WHERE ${platformConditions.join(' AND ')}` 
                : '';
            
            const platformDataRaw = await adRepository.query(`
                SELECT platform, COUNT(*) as count
                FROM ads, UNNEST(platforms) as platform
                ${platformWhere}
                GROUP BY platform
                ORDER BY count DESC
            `, platformParams);

            return {
                totalAds,
                activeAds,
                inactiveAds,
                adsOverTime: timeData.map((row: any) => ({
                    date: row.date,
                    active: parseInt(row.active, 10),
                    inactive: parseInt(row.inactive, 10),
                    total: parseInt(row.total, 10),
                })),
                platformDistribution: platformDataRaw.map((row: any) => ({
                    platform: row.platform,
                    count: parseInt(row.count, 10),
                })),
            };
        } catch (error) {
            throw new DatabaseError(`Failed to fetch stats: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
}

export const adService = {
    getAds,
    getAdById,
    getStats,
};
