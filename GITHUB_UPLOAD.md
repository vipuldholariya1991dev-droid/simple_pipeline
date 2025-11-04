# How to Upload to GitHub

This guide will help you upload the `simple_pipeline` project to GitHub.

## Step 1: Prepare the Repository

The `.gitignore` file is already configured to exclude:
- ✅ Python virtual environments (`venv/`)
- ✅ Node modules (`node_modules/`)
- ✅ Python cache files (`__pycache__/`)
- ✅ Database files and volumes
- ✅ Downloaded files
- ✅ IDE files

**What WILL be included:**
- ✅ All source code (`.py`, `.jsx`, `.css` files)
- ✅ Configuration files (`docker-compose.yml`, `requirements.txt`, `package.json`)
- ✅ Input CSV files (`keywords1.csv`, `keywords2.csv`)
- ✅ Documentation files (`README.md`, `SETUP_GUIDE.md`)
- ✅ All other necessary files

## Step 2: Create GitHub Repository

1. Go to [GitHub](https://github.com)
2. Click "New repository"
3. Name it: `simple-scraping-pipeline` (or any name you prefer)
4. Choose Public or Private
5. **DO NOT** initialize with README, .gitignore, or license (we already have these)
6. Click "Create repository"

## Step 3: Initialize Git and Upload

Open PowerShell/Terminal in the `simple_pipeline` folder:

```powershell
# Navigate to simple_pipeline folder
cd simple_pipeline

# Initialize git repository
git init

# Add all files (respects .gitignore)
git add .

# Commit files
git commit -m "Initial commit: Simple Scraping Pipeline"

# Add GitHub remote (replace <your-username> with your GitHub username)
git remote add origin https://github.com/<your-username>/simple-scraping-pipeline.git

# Push to GitHub
git branch -M main
git push -u origin main
```

## Step 4: Verify Upload

1. Go to your GitHub repository
2. Verify all files are present:
   - ✅ `backend/` folder with all Python files
   - ✅ `frontend/` folder with all React files
   - ✅ `keywords1.csv` and `keywords2.csv`
   - ✅ `README.md` and `SETUP_GUIDE.md`
   - ✅ `docker-compose.yml`
   - ✅ `.gitignore`

3. Verify excluded files are NOT present:
   - ❌ No `venv/` folder
   - ❌ No `node_modules/` folder
   - ❌ No `__pycache__/` folders
   - ❌ No database files

## What Gets Uploaded

### Included Files:
- ✅ All source code (`.py`, `.jsx`, `.css`)
- ✅ Configuration files (`.yml`, `.json`, `.txt`)
- ✅ Input CSV files (`keywords1.csv`, `keywords2.csv`)
- ✅ Documentation (`README.md`, `SETUP_GUIDE.md`)
- ✅ Setup scripts (`init_db.py`, `clear_database.py`)

### Excluded Files (via .gitignore):
- ❌ `venv/` - Python virtual environment
- ❌ `node_modules/` - Node.js dependencies
- ❌ `__pycache__/` - Python cache files
- ❌ `downloads/` - Downloaded scraped files
- ❌ `*.db`, `*.sqlite` - Database files
- ❌ `.env` - Environment variables
- ❌ IDE files (`.vscode/`, `.idea/`)

## Repository Structure on GitHub

```
simple-scraping-pipeline/
├── .gitignore
├── README.md
├── SETUP_GUIDE.md
├── GITHUB_UPLOAD.md
├── keywords1.csv
├── keywords2.csv
├── backend/
│   ├── app/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── routes/
│   │   │   └── scraping.py
│   │   └── scraper/
│   │       ├── base.py
│   │       ├── manager.py
│   │       ├── pdf_scraper.py
│   │       ├── image_scraper.py
│   │       └── youtube_scraper.py
│   ├── docker-compose.yml
│   ├── requirements.txt
│   ├── init_db.py
│   ├── clear_database.py
│   └── check_database.py
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   ├── index.css
    │   └── main.jsx
    ├── package.json
    ├── vite.config.js
    └── index.html
```

## After Uploading

Anyone can clone and setup the project:

```bash
git clone <your-repository-url>
cd simple-scraping-pipeline
# Follow SETUP_GUIDE.md for setup instructions
```

## Updating the Repository

After making changes:

```powershell
cd simple_pipeline

# Check what changed
git status

# Add changes
git add .

# Commit changes
git commit -m "Description of changes"

# Push to GitHub
git push
```

## Important Notes

1. **Never commit sensitive data**: API keys, passwords, etc.
2. **Database files excluded**: The `.gitignore` ensures database files are not uploaded
3. **Downloaded files excluded**: Scraped PDFs, images, etc. are not uploaded
4. **Input files included**: `keywords1.csv` and `keywords2.csv` are included as examples

## Need Help?

If you encounter issues:
- Check `.gitignore` is working: `git status` should not show excluded files
- Verify file sizes: Large files might need Git LFS
- Check GitHub file limits: Individual files must be < 100MB

