import { drizzle } from 'drizzle-orm/node-postgres';
import { Pool } from 'pg';
import { config } from '../config';
import * as schema from './schema';

let pool: Pool | null = null;
let dbInstance: ReturnType<typeof drizzle<typeof schema>> | null = null;

export function getDb() {
    if (!dbInstance) {
        throw new Error('Database not initialized. Call initializeDatabase() first.');
    }
    return dbInstance;
}

export async function initializeDatabase(): Promise<void> {
    try {
        pool = new Pool({
            connectionString: config.database.connectionString,
            max: 20,
            idleTimeoutMillis: 30000,
            connectionTimeoutMillis: 2000,
        });
        dbInstance = drizzle(pool, { schema });
        console.log('Database connection established via Drizzle');
    } catch (error) {
        console.error('Error during database initialization:', error);
        throw error;
    }
}

export async function closeDatabase(): Promise<void> {
    try {
        if (pool) {
            await pool.end();
            pool = null;
            dbInstance = null;
        }
        console.log('Database connection closed');
    } catch (error) {
        console.error('Error closing database connection:', error);
        throw error;
    }
}

export { schema };
