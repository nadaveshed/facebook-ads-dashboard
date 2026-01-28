import { query, param } from 'express-validator';

export const validateGetAds = [
    query('status')
        .optional()
        .isIn(['active', 'inactive'])
        .withMessage('Status must be either "active" or "inactive"'),
    query('platform')
        .optional()
        .isString()
        .trim()
        .notEmpty()
        .withMessage('Platform must be a non-empty string'),
    query('startDate')
        .optional()
        .isISO8601()
        .withMessage('startDate must be a valid ISO 8601 date'),
    query('endDate')
        .optional()
        .isISO8601()
        .withMessage('endDate must be a valid ISO 8601 date'),
    query('page')
        .optional()
        .isInt({ min: 1 })
        .withMessage('Page must be a positive integer'),
    query('pageSize')
        .optional()
        .isInt({ min: 1, max: 100 })
        .withMessage('Page size must be between 1 and 100'),
];

export const validateGetAdById = [
    param('id')
        .isInt({ min: 1 })
        .withMessage('ID must be a positive integer'),
];

export const validateGetStats = [
    query('platform')
        .optional()
        .isString()
        .trim()
        .notEmpty()
        .withMessage('Platform must be a non-empty string'),
    query('startDate')
        .optional()
        .isISO8601()
        .withMessage('startDate must be a valid ISO 8601 date'),
    query('endDate')
        .optional()
        .isISO8601()
        .withMessage('endDate must be a valid ISO 8601 date'),
];
