import { Entity, PrimaryGeneratedColumn, Column, CreateDateColumn, UpdateDateColumn, Index } from 'typeorm';

export enum AdStatus {
    ACTIVE = 'active',
    INACTIVE = 'inactive',
}

export enum AssetType {
    IMAGE = 'image',
    VIDEO = 'video',
    NONE = 'none',
}

@Entity('ads')
@Index('idx_ads_status', ['status'])
@Index('idx_ads_start_date', ['start_date'])
@Index('idx_ads_end_date', ['end_date'])
export class Ad {
    @PrimaryGeneratedColumn()
    id!: number;

    @Column({ type: 'varchar', length: 255, unique: true })
    ad_id!: string;

    @Column({ type: 'varchar', length: 255, unique: true })
    lib_id!: string;

    @Column({ type: 'varchar', length: 50 })
    status!: AdStatus;

    @Column({ type: 'text', array: true, default: '{}' })
    platforms!: string[];

    @Column({ type: 'date', nullable: true })
    start_date!: Date | null;

    @Column({ type: 'date', nullable: true })
    end_date!: Date | null;

    @Column({ type: 'varchar', length: 50, nullable: true })
    asset_type!: AssetType | null;

    @Column({ type: 'text', nullable: true })
    asset_url!: string | null;

    @Column({ type: 'varchar', length: 500, nullable: true })
    asset_path!: string | null;

    @Column({ type: 'text', nullable: true })
    ad_content!: string | null;

    @Column({ type: 'varchar', length: 255, default: 'Nike' })
    advertiser_name!: string;

    @CreateDateColumn({ type: 'timestamptz' })
    created_at!: Date;

    @UpdateDateColumn({ type: 'timestamptz' })
    updated_at!: Date;
}
