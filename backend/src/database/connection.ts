
import { Pool, PoolClient } from 'pg';
import { config } from '../config';

class Database {
    private pool: Pool;
    private static instance: Database;

    private constructor() {
        this.pool = new Pool({
            connectionString: config.database.connectionString,
            max: 20,
            idleTimeoutMillis: 30000,
            connectionTimeoutMillis: 2000,
        });

        this.pool.on('error', (err) => {
            console.error('Unexpected database error:', err);
        });
    }

    public static getInstance(): Database {
        if (!Database.instance) {
            Database.instance = new Database();
        }
        return Database.instance;
    }

    public async getClient(): Promise<PoolClient> {
        return await this.pool.connect();
    }

    public async query<T>(text: string, params?: any[]): Promise<T[]> {
        const result = await this.pool.query(text, params);
        return result.rows as T[];
    }

    public async close(): Promise<void> {
        await this.pool.end();
    }
}

export const db = Database.getInstance();
