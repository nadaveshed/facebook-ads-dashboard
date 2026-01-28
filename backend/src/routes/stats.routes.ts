import { Router } from 'express';
import { adsController } from '../controllers';
import { validateGetStats } from '../validators/ads.validator';
import { validate } from '../middleware/validation.middleware';

const router = Router();

router.get('/', validate(validateGetStats), (req, res, next) => adsController.getStats(req, res, next));

export default router;
