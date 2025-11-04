# How to View Backend Console Logs

## ⚠️ IMPORTANT: Logs Only Appear When Scraping is Running!

The logs will **ONLY** appear when you actually run a scraping task. If the backend is just running (showing "Application startup complete"), you won't see any scraping logs yet.

## Where to Find the Logs

The backend console logs appear in the **PowerShell or terminal window** where you started the backend server.

## Steps to View Logs

### Step 1: Make Sure Backend is Running

1. **Find the PowerShell/terminal window** where you started the backend
   - Look for a window showing:
     ```
     INFO:     Started server process [...]
     INFO:     Application startup complete.
     INFO:     Uvicorn running on http://0.0.0.0:8001
     ```

### Step 2: Run a Scraping Task

1. **Open your browser** and go to `http://localhost:3000` (or wherever your frontend is running)
2. **Select CSV files** (keywords1.csv and keywords2.csv)
3. **Check the content types** you want to scrape (PDF, Image, YouTube)
4. **Click "Start Scraping"**

### Step 3: Watch the Backend Console

**NOW** go back to the PowerShell window where the backend is running. You should see logs appearing like:

```
🚀 Starting scraping task task_1234567890 for 10 keywords
   Content types: PDF=True, Image=True, YouTube=True
🔍 Starting PDF scraping for 'keyword1'...
  ✅ PDF scraper returned 1 items for 'keyword1'
    📄 PDF items to process: 1
    ✅ Added PDF 1/1: https://example.com/file.pdf
    📊 PDF count for keyword 'keyword1': 1
✅ Committed all items for keyword 'keyword1': PDF=1, IMG=2, YT=1
📊 Final counts for keyword 'keyword1': PDF=1, IMG=2, YT=1
📊 Progress update for 'keyword1': PDF=1, IMG=2, YT=1
📊 Total progress: PDF=1 (was 0 + 1), IMG=2 (was 0 + 2), YT=1 (was 0 + 1)
```

### Option 2: Start Backend in a New Window

1. **Open a new PowerShell window**
2. **Navigate to the backend directory:**
   ```powershell
   cd E:\work\generic_pipeline\simple_pipeline\backend
   ```

3. **Start the backend:**
   ```powershell
   .\restart_backend.ps1
   ```
   
   OR manually:
   ```powershell
   .\venv\Scripts\Activate.ps1
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
   ```

4. **Keep this window open** - all logs will appear here!

## What Logs to Look For

When you run a scraping task, you'll see logs like:

```
🔍 Starting PDF scraping for 'keyword'...
  ✅ PDF scraper returned 3 items for 'keyword'
    📄 PDF items to process: 3
    ✅ Added PDF 1/1: https://example.com/file.pdf
    📊 PDF count for keyword 'keyword': 1
✅ Committed all items for keyword 'keyword': PDF=1, IMG=16, YT=9
📊 Final counts for keyword 'keyword': PDF=1, IMG=16, YT=9
📊 Progress update for 'keyword': PDF=1, IMG=16, YT=9
📊 Total progress: PDF=1 (was 0 + 1), IMG=16 (was 0 + 16), YT=9 (was 0 + 9)
```

## Tips

- **Keep the backend console window visible** while scraping
- **Scroll up** to see earlier logs if needed
- **Look for** the `📊` emoji - that's where count updates appear
- **Check for errors** - they'll show with `❌` or error messages

## If You Can't Find the Backend Window

1. Check if the backend is running:
   ```powershell
   Get-NetTCPConnection -LocalPort 8001
   ```

2. If it's running but you can't see the window:
   - The window might be minimized
   - Check your taskbar for a PowerShell window
   - Or restart the backend in a new window (Option 2 above)

