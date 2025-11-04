# Simple Pipeline - Setup Guide for New Laptop

This guide will help you set up the entire `simple_pipeline` project on a new laptop.

## Prerequisites

1. **Docker Desktop** - [Download here](https://www.docker.com/products/docker-desktop/)
   - Required for PostgreSQL database and pgAdmin
   
2. **Python 3.8+** - [Download here](https://www.python.org/downloads/)
   - Required for backend API
   
3. **Node.js 16+ and npm** - [Download here](https://nodejs.org/)
   - Required for frontend React app

4. **Git** (optional) - For cloning repository or copying files

## Step-by-Step Setup

### Step 1: Copy Project Files

Copy the entire `simple_pipeline` folder to the new laptop. You can:
- Copy the folder via USB/external drive
- Use Git to clone the repository
- Zip the folder and transfer it

### Step 2: Start Docker Desktop

1. Open Docker Desktop on the new laptop
2. Wait for Docker to start (whale icon in system tray should be running)
3. Verify Docker is running: Open PowerShell/Terminal and run:
   ```powershell
   docker --version
   ```

### Step 3: Start Database (PostgreSQL + pgAdmin)

1. Open PowerShell/Terminal
2. Navigate to the backend folder:
   ```powershell
   cd simple_pipeline\backend
   ```
   
3. Start Docker containers:
   ```powershell
   docker-compose up -d
   ```
   
4. Verify containers are running:
   ```powershell
   docker-compose ps
   ```
   
   You should see:
   - `db` (PostgreSQL) - running
   - `pgadmin` (pgAdmin) - running

5. Wait 10-15 seconds for database to initialize

### Step 4: Create Database and Tables

The database will be created automatically by Docker Compose. You just need to initialize the tables:

1. Navigate to backend folder:
   ```powershell
   cd simple_pipeline\backend
   ```

2. Create Python virtual environment (if not exists):
   ```powershell
   python -m venv venv
   ```

3. Activate virtual environment:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```
   (If you get an error, run: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`)

4. Install Python dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

5. Initialize database tables:
   ```powershell
   python init_db.py
   ```
   
   Or alternatively:
   ```powershell
   python -c "from app.database import init_db; init_db()"
   ```

### Step 6: Setup Backend

1. Navigate to backend folder:
   ```powershell
   cd simple_pipeline\backend
   ```

2. Activate virtual environment (if not active):
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

3. Start the backend server:
   ```powershell
   uvicorn app.main:app --reload --port 8001
   ```

4. Keep this terminal window open - backend should be running on `http://localhost:8001`

### Step 7: Setup Frontend

1. Open a NEW PowerShell/Terminal window

2. Navigate to frontend folder:
   ```powershell
   cd simple_pipeline\frontend
   ```

3. Install npm dependencies:
   ```powershell
   npm install
   ```

4. Start the frontend development server:
   ```powershell
   npm run dev
   ```

5. Keep this terminal window open - frontend should be running on `http://localhost:5174`

### Step 8: Verify Everything is Working

1. **Backend API**: Open browser and go to `http://localhost:8001/docs`
   - Should see FastAPI documentation page

2. **Frontend UI**: Open browser and go to `http://localhost:5174`
   - Should see the scraping interface

3. **Database (pgAdmin)**: Open browser and go to `http://localhost:5050`
   - Login with:
     - Email: `admin@admin.com`
     - Password: `admin`
   - Connect to server:
     - Host: `db` (not localhost!)
     - Port: `5432`
     - Username: `postgres`
     - Password: `postgres`

## Quick Start Commands (After Initial Setup)

### Start All Services:

**Terminal 1 - Database:**
```powershell
cd simple_pipeline\backend
docker-compose up -d
```

**Terminal 2 - Backend:**
```powershell
cd simple_pipeline\backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8001
```

**Terminal 3 - Frontend:**
```powershell
cd simple_pipeline\frontend
npm run dev
```

## Troubleshooting

### Database Connection Error
- Make sure Docker Desktop is running
- Check containers: `docker-compose ps`
- Restart containers: `docker-compose restart`

### Backend Port Already in Use
- Change port in `uvicorn` command: `--port 8002`
- Update frontend `API_BASE` in `App.jsx` to match new port

### Frontend Port Already in Use
- Vite will automatically use next available port (e.g., 5175)
- Check terminal output for actual port

### Python Module Not Found
- Make sure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`

### Database Tables Not Created
- Run: `python -c "from app.database import init_db; init_db()"`

## Project Structure

```
simple_pipeline/
├── backend/
│   ├── app/
│   │   ├── config.py          # Configuration
│   │   ├── database.py         # Database models
│   │   ├── main.py            # FastAPI app
│   │   ├── routes/             # API routes
│   │   └── scraper/           # Scraping modules
│   ├── docker-compose.yml     # Docker services
│   ├── requirements.txt       # Python dependencies
│   └── venv/                  # Python virtual environment
│
└── frontend/
    ├── src/
    │   ├── App.jsx            # Main React component
    │   └── index.css          # Styles
    ├── package.json           # Node dependencies
    └── node_modules/          # Node packages
```

## Configuration

No API keys or special configuration needed - the project uses:
- DuckDuckGo for PDF scraping (free, no API key)
- Bing Image API (if configured, otherwise DuckDuckGo)
- yt-dlp for YouTube scraping (free)

## Ports Used

- **Frontend**: `5174` (Vite default)
- **Backend**: `8001`
- **PostgreSQL**: `5432` (internal Docker network)
- **pgAdmin**: `5050`

## Stopping Services

1. **Stop Frontend**: Press `Ctrl+C` in frontend terminal
2. **Stop Backend**: Press `Ctrl+C` in backend terminal
3. **Stop Database**: 
   ```powershell
   cd simple_pipeline\backend
   docker-compose down
   ```

## Need Help?

If you encounter any issues:
1. Check all services are running (3 terminal windows)
2. Verify Docker Desktop is running
3. Check port conflicts
4. Review error messages in terminal windows

