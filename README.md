# Simple Scraping Pipeline

A modern, scalable web scraping pipeline that extracts PDFs, Images, and YouTube videos based on keyword CSV files. Features a clean React UI and FastAPI backend with PostgreSQL database.

## Features

- 📄 **PDF Scraping** - Extract PDF documents using DuckDuckGo
- 🖼️ **Image Scraping** - Extract images using Bing Image API
- 🎥 **YouTube Scraping** - Extract YouTube videos using yt-dlp
- 📊 **Database Storage** - PostgreSQL with pgAdmin for data management
- 🎨 **Modern UI** - Clean, professional React interface
- 📥 **Bulk Downloads** - Download all items as ZIP (PDFs/Images) or CSV (YouTube)
- 🔍 **Real-time Progress** - Live tracking of scraping progress
- ✅ **Duplicate Detection** - Prevents duplicate items
- 📁 **Multi-file Support** - Upload multiple CSV files at once

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: React + Vite
- **Database**: PostgreSQL (Docker)
- **Scraping**: DuckDuckGo, Bing Image API, yt-dlp

## Quick Start

### Prerequisites

- Docker Desktop
- Python 3.8+
- Node.js 16+ and npm

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd simple_pipeline
   ```

2. **Start Database**
   ```bash
   cd backend
   docker-compose up -d
   ```

3. **Setup Backend**
   ```bash
   cd backend
   python -m venv venv
   .\venv\Scripts\Activate.ps1  # Windows
   # or: source venv/bin/activate  # Linux/Mac
   pip install -r requirements.txt
   python init_db.py
   uvicorn app.main:app --reload --port 8001
   ```

4. **Setup Frontend**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

5. **Access the Application**
   - Frontend: http://localhost:5174
   - Backend API: http://localhost:8001
   - API Docs: http://localhost:8001/docs
   - pgAdmin: http://localhost:5050

## Usage

1. **Upload CSV Files**: Select one or more CSV files containing keywords (one keyword per line)
2. **Select Content Types**: Check PDF, Image, and/or YouTube checkboxes
3. **Start Scraping**: Click "Start Scraping" and monitor real-time progress
4. **Download Results**: Click "Download Scraped Data" to download all items

## Project Structure

```
simple_pipeline/
├── backend/
│   ├── app/
│   │   ├── config.py          # Configuration settings
│   │   ├── database.py         # Database models
│   │   ├── main.py            # FastAPI application
│   │   ├── models.py          # Pydantic models
│   │   ├── routes/
│   │   │   └── scraping.py    # API endpoints
│   │   └── scraper/
│   │       ├── base.py         # Base scraper class
│   │       ├── manager.py      # Scraper manager
│   │       ├── pdf_scraper.py  # PDF scraper
│   │       ├── image_scraper.py # Image scraper
│   │       └── youtube_scraper.py # YouTube scraper
│   ├── docker-compose.yml     # Docker services
│   ├── requirements.txt      # Python dependencies
│   ├── init_db.py            # Database initialization
│   └── clear_database.py     # Database clearing script
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx           # Main React component
│   │   ├── index.css         # Styles
│   │   └── main.jsx          # React entry point
│   └── package.json          # Node dependencies
│
├── keywords1.csv            # Sample input file 1
├── keywords2.csv            # Sample input file 2
├── SETUP_GUIDE.md          # Detailed setup instructions
└── README.md               # This file
```

## Configuration

### Scraping Limits

Edit `backend/app/config.py`:
```python
MAX_RESULTS_PER_KEYWORD: int = 2  # Items per keyword
```

### Database

Default connection: `postgresql://postgres:postgres@localhost:5432/simple_scraping_db`

Edit `backend/app/config.py` to change database settings.

## API Endpoints

- `POST /api/scraping/upload-csv` - Upload CSV files and start scraping
- `GET /api/scraping/progress/{task_id}` - Get scraping progress
- `GET /api/scraping/items` - Get scraped items (filtered by task_id)
- `GET /api/scraping/download-bulk` - Download items as ZIP (PDF/Image)
- `GET /api/scraping/download-youtube-csv` - Download YouTube items as CSV
- `POST /api/scraping/clear-database` - Clear all items from database

## Troubleshooting

See `SETUP_GUIDE.md` for detailed troubleshooting steps.

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
