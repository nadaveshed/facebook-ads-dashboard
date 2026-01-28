import { DataSource } from 'typeorm';
import { config } from '../config';
import { Ad } from '../entities';

export const AppDataSource = new DataSource({
    type: 'postgres',
    url: config.database.connectionString,
    entities: [Ad],
    synchronize: false, // Use migrations or manual schema
    logging: false,
});
