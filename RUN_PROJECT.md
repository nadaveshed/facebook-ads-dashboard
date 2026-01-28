# הוראות הרצת הפרויקט

## ⚠️ דרישות מוקדמות

1. **Docker Desktop** - חייב להיות מופעל
2. **Ports זמינים**: 3000, 3001, 5432

---

## 🚀 הרצה עם Docker (מומלץ)

### שלב 1: הפעל Docker Desktop
- פתח את Docker Desktop
- המתן עד שהוא מוכן (אייקון ירוק)

### שלב 2: הרץ את הפרויקט
```bash
# מהתיקייה הראשית של הפרויקט
docker-compose up --build
```

### שלב 3: גש לאפליקציה
- **Dashboard**: http://localhost:3000
- **API**: http://localhost:3001/api/ads
- **Health Check**: http://localhost:3001/health

### פקודות נוספות:
```bash
# הרצה ברקע
docker-compose up -d --build

# צפייה בלוגים
docker-compose logs -f

# עצירת הפרויקט
docker-compose down

# בדיקת סטטוס
docker-compose ps
```

---

## 💻 הרצה בלי Docker (Development Mode)

### דרישות:
- Node.js 20+ מותקן
- PostgreSQL 15 מותקן ומריץ
- npm מותקן

### שלב 1: הגדר Database
```bash
# צור database
createdb ads_db

# או עם psql
psql -U postgres
CREATE DATABASE ads_db;
\q
```

### שלב 2: הרץ את ה-Backend
```bash
cd backend
npm install

# הגדר משתני סביבה
# צור .env file עם:
# DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ads_db
# PORT=3001
# ASSETS_DIR=./assets

npm run dev
```

### שלב 3: הרץ את ה-Frontend (טרמינל נפרד)
```bash
cd frontend
npm install
npm start
```

### שלב 4: הרץ את ה-Scraper (אופציונלי)
```bash
cd scraper
pip install -r requirements.txt

# הגדר משתני סביבה
# DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ads_db
# ASSETS_DIR=./assets
# USE_DEMO_DATA=true

python -m src.main
```

---

## 🔍 פתרון בעיות

### Docker Desktop לא פועל
**שגיאה:** `unable to connect to docker API`

**פתרון:**
1. פתח את Docker Desktop
2. המתן עד שהוא מוכן
3. נסה שוב: `docker-compose up --build`

### Port כבר בשימוש
**שגיאה:** `port is already allocated`

**פתרון:**
```bash
# בדוק מה משתמש ב-port
netstat -ano | findstr :3000
netstat -ano | findstr :3001
netstat -ano | findstr :5432

# או עצור את השירותים הישנים
docker-compose down
```

### Database לא מתחבר
**שגיאה:** `database connection failed`

**פתרון:**
1. בדוק ש-PostgreSQL רץ: `docker-compose ps`
2. בדוק את ה-logs: `docker-compose logs db`
3. המתן כמה שניות - ה-database צריך זמן להתחיל

---

## 📝 הערות

- הפרויקט משתמש ב-**demo data** כברירת מחדל
- ה-scraper יוצר 55 מודעות דמו אוטומטית
- כל השירותים מתחילים אוטומטית עם `docker-compose up`
- ה-database מתאתחל עם schema אוטומטית

---

## ✅ בדיקת תקינות

לאחר ההרצה, בדוק:

1. **Backend Health:**
   ```bash
   curl http://localhost:3001/health
   ```

2. **API Endpoint:**
   ```bash
   curl http://localhost:3001/api/ads
   ```

3. **Frontend:**
   - פתח דפדפן: http://localhost:3000
   - אמור לראות את ה-Dashboard
