import { Request, Response, NextFunction } from 'express';
import { adService } from '../services';
import { AdFilters } from '../models';
import { NotFoundError } from '../errors/AppError';

async function getAds(req: Request, res: Response, next: NextFunction): Promise<void> {
    try {
        const { status, platform, startDate, endDate, page, pageSize } = req.query;

        const filters: AdFilters = {};
        if (status === 'active' || status === 'inactive') {
            filters.status = status;
        }
        if (typeof platform === 'string') {
            filters.platform = platform;
        }
        if (typeof startDate === 'string') {
            filters.startDate = startDate;
        }
        if (typeof endDate === 'string') {
            filters.endDate = endDate;
        }

        const pageNum = parseInt(page as string, 10) || 1;
        const size = parseInt(pageSize as string, 10) || 20;

        const result = await adService.getAds(filters, pageNum, size);
        res.json(result);
    } catch (error) {
        next(error);
    }
}

async function getAdById(req: Request, res: Response, next: NextFunction): Promise<void> {
    try {
        const id = parseInt(req.params.id, 10);
        const ad = await adService.getAdById(id);
        if (!ad) {
            throw new NotFoundError('Ad not found');
        }

        res.json(ad);
    } catch (error) {
        next(error);
    }
}

async function getStats(req: Request, res: Response, next: NextFunction): Promise<void> {
    try {
        const { platform, startDate, endDate } = req.query;

        const filters: AdFilters = {};
        if (typeof platform === 'string') {
            filters.platform = platform;
        }
        if (typeof startDate === 'string') {
            filters.startDate = startDate;
        }
        if (typeof endDate === 'string') {
            filters.endDate = endDate;
        }

        const stats = await adService.getStats(filters);
        res.json(stats);
    } catch (error) {
        next(error);
    }
}

export const adsController = {
    getAds,
    getAdById,
    getStats,
};
