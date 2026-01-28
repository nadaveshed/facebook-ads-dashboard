import { Request, Response, NextFunction } from 'express';
import { AppError } from '../errors/AppError';

export interface ApiError extends Error {
    statusCode?: number;
    isOperational?: boolean;
}

export function errorHandler(
    err: Error | AppError | ApiError,
    req: Request,
    res: Response,
    next: NextFunction
): void {
    if (err instanceof AppError) {
        const statusCode = err.statusCode || 500;
        const message = err.message || 'Internal Server Error';

        console.error(`[ERROR] ${req.method} ${req.path}:`, err);

        res.status(statusCode).json({
            error: {
                message,
                statusCode,
                ...(err instanceof AppError && 'errors' in err && { errors: (err as any).errors }),
                ...(process.env.NODE_ENV === 'development' && { stack: err.stack }),
            },
        });
        return;
    }

    const statusCode = (err as ApiError).statusCode || 500;
    const message = err.message || 'Internal Server Error';

    console.error(`[ERROR] ${req.method} ${req.path}:`, err);

    res.status(statusCode).json({
        error: {
            message,
            statusCode,
            ...(process.env.NODE_ENV === 'development' && { stack: err.stack }),
        },
    });
}

export function notFoundHandler(req: Request, res: Response): void {
    res.status(404).json({
        error: {
            message: `Route ${req.method} ${req.path} not found`,
            statusCode: 404,
        },
    });
}
