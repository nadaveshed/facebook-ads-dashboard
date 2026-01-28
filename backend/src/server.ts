
import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import fs from 'fs';
import path from 'path';

import 'reflect-metadata';
import { config } from './config';
import { adsRoutes, statsRoutes } from './routes';
import { errorHandler, notFoundHandler } from './middleware';
import { initializeDatabase } from './database/data-source';

const app = express();

app.use(helmet({
    crossOriginResourcePolicy: { policy: 'cross-origin' },
}));

app.use(cors({
    origin: process.env.FRONTEND_URL || 'http://localhost:3000',
    credentials: true,
}));

app.use(morgan('combined'));

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.get('/health', (req, res) => {
    res.json({ status: 'healthy', timestamp: new Date().toISOString() });
});

app.use('/api/ads', adsRoutes);
app.use('/api/stats', statsRoutes);

app.use('/assets', express.static(config.assets.directory, {
    maxAge: '1d',
    etag: true,
    index: false,
    dotfiles: 'ignore',
}));

app.use(notFoundHandler);
app.use(errorHandler);

const startServer = async () => {
    try {
        await initializeDatabase();

        const assetsDir = config.assets.directory;
        
        if (!fs.existsSync(assetsDir)) {
            fs.mkdirSync(assetsDir, { recursive: true });
            console.log(`Created assets directory: ${assetsDir}`);
        }
        
        const assetFiles = fs.readdirSync(assetsDir).filter((f: string) => f !== '.gitkeep');
        console.log(`Assets directory contains ${assetFiles.length} files: ${assetFiles.slice(0, 5).join(', ')}${assetFiles.length > 5 ? '...' : ''}`);

        app.listen(config.server.port, '0.0.0.0', () => {
            console.log('='.repeat(50));
            console.log('Facebook Ads Dashboard - Backend API');
            console.log('='.repeat(50));
            console.log(`Environment: ${config.server.env}`);
            console.log(`Server running on port: ${config.server.port}`);
            console.log(`Assets directory: ${config.assets.directory}`);
            console.log(`Assets available: ${assetFiles.length} files`);
            console.log('='.repeat(50));
        });
    } catch (error) {
        console.error('Failed to start server:', error);
        process.exit(1);
    }
};

startServer();

export default app;
