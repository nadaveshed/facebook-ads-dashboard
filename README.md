# Facebook Ads Dashboard

A POC system that scrapes Facebook Ads Library data for Nike and displays it in a web dashboard.

## Overview

This project consists of four Dockerized services:

1. **PostgreSQL Database** - Stores scraped ad data
2. **Python Scraper** - Scrapes Nike ads from Facebook Ads Library using Selenium
3. **Node.js Backend** - Express API serving ad data with filtering
4. **React Frontend** - Dashboard UI with charts and filtering

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Port 3000, 3001, and 5432 available

### Run the Application

1. **Copy env and set sensitive values** (passwords, URLs):
   ```bash
   cp .env.example .env
   # Edit .env and set at least POSTGRES_PASSWORD (and DATABASE_URL if not using Docker defaults)
   ```

2. **Start with Docker**:
   ```bash
   cd facebook-ads-dashboard
   docker-compose up --build
   ```

Wait for all services to start (scraper will populate demo data), then open:

- **Dashboard**: http://localhost:3000
- **API**: http://localhost:3001/api/ads

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend    │────▶│  PostgreSQL │
│  (React)    │     │  (Node.js)   │     │   Database  │
│  :3000      │     │  :3001       │     │   :5432     │
└─────────────┘     └──────────────┘     └─────────────┘
                           ▲
                           │
                    ┌──────┴──────┐
                    │   Scraper   │
                    │  (Python)   │
                    └─────────────┘
```

## Features

### Dashboard
- **Summary Stats**: Total, active, and inactive ad counts
- **Time Series Chart**: Visualize ads over time (Recharts)
- **Ads Gallery**: Grid of ad cards with asset previews
- **Filters**: Status (active/inactive), Platform, Date range
- **Pagination**: Navigate through ads

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ads` | GET | List ads with filters (status, platform, dates) |
| `/api/ads/:id` | GET | Get single ad by ID |
| `/api/stats` | GET | Dashboard statistics |
| `/assets/:file` | GET | Serve ad assets (images/videos) |

### Query Parameters

```
GET /api/ads?status=active&platform=facebook&startDate=2025-01-01&endDate=2025-12-31&page=1&pageSize=20
```

## Project Structure

```
facebook-ads-dashboard/
├── docker-compose.yml
├── database/
│   └── init.sql              # Database schema
├── scraper/                   # Python Scraper Service
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
│       ├── main.py            # Entry point
│       ├── config/            # Configuration
│       ├── database/          # DB connection & repository
│       ├── models/            # Data models
│       ├── scraper/           # Selenium scraper
│       └── utils/             # File utilities
├── backend/                   # Node.js API
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       ├── index.ts           # Express server
│       ├── config/            # Configuration
│       ├── controllers/       # Request handlers
│       ├── database/          # DB connection
│       ├── middleware/        # Error handling
│       ├── models/            # TypeScript types
│       ├── routes/            # API routes
│       └── services/          # Business logic
└── frontend/                  # React Dashboard
    ├── Dockerfile
    ├── nginx.conf
    ├── package.json
    └── src/
        ├── main.tsx           # Entry point
        ├── App.tsx            # Main component
        ├── components/        # UI components
        ├── hooks/             # Custom hooks
        ├── pages/             # Page components
        ├── services/          # API client
        └── types/             # TypeScript types
```

## Scraping Approach

The scraper uses **Selenium** with headless Chrome to:

1. Navigate to Facebook Ads Library for Nike (page ID: 15087023444)
2. Scroll page to load ads via infinite scroll
3. Extract ad data (ID, status, platforms, dates, content)
4. Download ad assets (images/videos) to local storage
5. Store data in PostgreSQL

**Note**: The scraper scrapes real ads from Facebook Ads Library. Configure `MAX_ADS` environment variable to control how many ads to scrape (default: 50).

## Database Schema

```sql
CREATE TABLE ads (
    id SERIAL PRIMARY KEY,
    ad_id VARCHAR(255) UNIQUE NOT NULL,
    status VARCHAR(50) NOT NULL,        -- 'active' or 'inactive'
    platforms TEXT[],                    -- Array of platforms
    start_date DATE,
    end_date DATE,
    asset_type VARCHAR(50),             -- 'image', 'video', 'none'
    asset_path VARCHAR(500),            -- Path to asset file
    ad_content TEXT,                    -- Ad text/description
    advertiser_name VARCHAR(255),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

## Development

### Backend Development

```bash
cd backend
npm install
npm run dev     # Runs on http://localhost:3001
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev     # Runs on http://localhost:3000
```

### Run Database Only

```bash
docker-compose up db -d
```

## Technology Stack

| Component | Technologies |
|-----------|--------------|
| Database | PostgreSQL 15 |
| Scraper | Python 3.11, Selenium, psycopg2 |
| Backend | Node.js 20, Express, TypeScript, pg |
| Frontend | React 18, TypeScript, Vite, Recharts |
| Deployment | Docker, nginx |

## Environment Variables

Sensitive and config values live in **`.env`** (not committed). Copy `.env.example` to `.env` and set your values.

| Variable | Used by | Description |
|----------|---------|-------------|
| `POSTGRES_USER` | docker-compose, db | Database user |
| `POSTGRES_PASSWORD` | docker-compose, db | Database password (set a strong one in production) |
| `POSTGRES_DB` | docker-compose, db | Database name |
| `DATABASE_URL` | backend, scraper, drizzle | Full connection string (e.g. `postgresql://user:pass@host:5432/db`) |
| `PORT` | backend | API port (default 3001) |
| `ASSETS_DIR` | backend, scraper | Path to ad assets |
| `FRONTEND_URL` | backend | Allowed CORS origin |
| `TARGET_URL` | scraper | Facebook Ads Library URL to scrape |
| `MAX_ADS` | scraper | Max ads to scrape |
| `SCROLL_DELAY_MS` | scraper | Scroll delay (ms) |
| `HEADLESS` | scraper | Run browser headless (true/false) |

Optional for Docker: `DB_PORT`, `BACKEND_PORT`, `FRONTEND_PORT` to override published ports.

## License

MIT
