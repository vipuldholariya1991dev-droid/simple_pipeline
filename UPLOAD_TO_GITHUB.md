# Upload to GitHub - Step by Step

## ⚠️ Important Note

Including `node_modules/` is NOT recommended because:
- It's very large (can be 100+ MB)
- Can cause upload timeouts
- Platform-specific files may cause issues
- Usually recreated with `npm install`

However, since you requested it, `node_modules/` will be included.

## Step 1: Create GitHub Repository

1. Go to [GitHub.com](https://github.com) and sign in
2. Click the **"+"** icon in the top right → **"New repository"**
3. Repository name: `simple-scraping-pipeline` (or any name you prefer)
4. Description: "Modern web scraping pipeline for PDFs, Images, and YouTube videos"
5. Choose **Public** or **Private**
6. **DO NOT** check "Add a README file" (we already have one)
7. **DO NOT** check "Add .gitignore" (we already have one)
8. Click **"Create repository"**

## Step 2: Copy Repository URL

After creating the repository, GitHub will show you a URL like:
```
https://github.com/YOUR_USERNAME/simple-scraping-pipeline.git
```

**Copy this URL** - you'll need it in the next step.

## Step 3: Upload Files to GitHub

Open PowerShell/Terminal in the `simple_pipeline` folder:

```powershell
# Navigate to simple_pipeline folder
cd E:\work\generic_pipeline\simple_pipeline

# Initialize git repository
git init

# Check what files will be added (optional - to verify)
git status

# Add all files (including node_modules)
git add .

# Commit files
git commit -m "Initial commit: Simple Scraping Pipeline with all dependencies"

# Add your GitHub repository (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/simple-scraping-pipeline.git

# Set main branch
git branch -M main

# Push to GitHub (this may take a while if node_modules is large)
git push -u origin main
```

## Step 4: Verify Upload

1. Go to your GitHub repository page
2. Refresh the page
3. Verify all files are present:
   - ✅ `backend/` folder
   - ✅ `frontend/` folder (including `node_modules/`)
   - ✅ `keywords1.csv` and `keywords2.csv`
   - ✅ All documentation files
   - ✅ `.gitignore`

## Your GitHub Repository URL

After pushing, your repository will be available at:
```
https://github.com/YOUR_USERNAME/simple-scraping-pipeline
```

## Troubleshooting

### Error: "Repository not found"
- Make sure you created the repository on GitHub first
- Check the repository name matches in the `git remote add origin` command
- Verify your GitHub username is correct

### Error: "Authentication failed"
- GitHub may require authentication via Personal Access Token
- Go to GitHub Settings → Developer settings → Personal access tokens
- Create a new token with `repo` permissions
- Use token as password when prompted

### Error: "Large file detected"
- If `node_modules/` is too large, GitHub may reject it
- Consider using Git LFS: `git lfs install` then `git lfs track "node_modules/**"`

### Upload is taking too long
- `node_modules/` can be very large (100+ MB)
- Be patient, it may take several minutes
- Check your internet connection

## Alternative: Exclude node_modules (Recommended)

If you encounter issues, you can exclude `node_modules/`:

1. Edit `.gitignore` and uncomment `node_modules/`
2. Remove from git: `git rm -r --cached node_modules`
3. Commit: `git commit -m "Remove node_modules from git"`
4. Push: `git push`

Then users can run `npm install` after cloning.

## Quick Commands Summary

```powershell
cd E:\work\generic_pipeline\simple_pipeline
git init
git add .
git commit -m "Initial commit: Simple Scraping Pipeline"
git remote add origin https://github.com/YOUR_USERNAME/simple-scraping-pipeline.git
git branch -M main
git push -u origin main
```

Replace `YOUR_USERNAME` with your actual GitHub username!

