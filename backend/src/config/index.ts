interface DatabaseConfig {
    connectionString: string;
}

interface ServerConfig {
    port: number;
    env: string;
}

interface AssetsConfig {
    directory: string;
}

export interface AppConfig {
    database: DatabaseConfig;
    server: ServerConfig;
    assets: AssetsConfig;
}

function loadConfig(): AppConfig {
    return {
        database: {
            connectionString: process.env.DATABASE_URL || 'postgresql://postgres:postgres@localhost:5432/ads_db',
        },
        server: {
            port: parseInt(process.env.PORT || '3001', 10),
            env: process.env.NODE_ENV || 'development',
        },
        assets: {
            directory: process.env.ASSETS_DIR || './assets',
        },
    };
}

export const config = loadConfig();
