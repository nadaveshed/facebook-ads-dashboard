import { Router } from 'express';
import { adsController } from '../controllers';
import { validateGetAds, validateGetAdById } from '../validators/ads.validator';
import { validate } from '../middleware/validation.middleware';

const router = Router();

router.get('/', validate(validateGetAds), (req, res, next) => adsController.getAds(req, res, next));

router.get('/:id', validate(validateGetAdById), (req, res, next) => adsController.getAdById(req, res, next));

export default router;
