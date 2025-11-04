# Quick Start Guide

## 🚀 Start the Simple Pipeline

### 1. Start Backend

```powershell
cd simple_pipeline\backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### 2. Start Frontend (New Terminal)

```powershell
cd simple_pipeline\frontend
npm install
npm run dev
```

### 3. Open Browser

Go to: **http://localhost:5174**

## 📝 Test with Sample Files

1. Click "Choose CSV Files (Multiple)"
2. Select both `keywords1.csv` and `keywords2.csv`
3. Check all content types (PDF, Image, YouTube)
4. Click "Start Scraping"

## ✅ Expected Results

- **Keywords1.csv**: 5 keywords → 10 images, 10 PDFs, 10 YouTube (30 items)
- **Keywords2.csv**: 5 keywords → 10 images, 10 PDFs, 10 YouTube (30 items)
- **Total**: 60 items (2 per keyword per type)

## 🔍 Key Features

- ✅ Multiple CSV file support
- ✅ 2 items per keyword (configurable)
- ✅ Duplicate detection across all files
- ✅ Modern, simplified UI
- ✅ Real-time progress
- ✅ Auto-download on click

## 📊 Database

- Default: PostgreSQL `simple_scraping_db` on `localhost:5432`
- Duplicates are automatically filtered by URL and content hash

