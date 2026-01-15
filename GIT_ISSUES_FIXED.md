# Git Issues Fixed

## Issues Identified

1. **Large files in git history** causing push failures:
   - `data/all-data.xlsx` (146.32 MB) - exceeds GitHub's 100 MB limit
   - `scoring_input.csv` (119.13 MB) - exceeds GitHub's 100 MB limit  
   - `data/train.csv` (80.85 MB) - exceeds GitHub's recommended 50 MB limit

2. **No .gitignore file** - large files were being tracked

3. **Remote naming mismatch** - remote was named "customer-churn" but code expected "origin"

4. **No upstream branch** - main branch had no upstream tracking configured

## Fixes Applied

### ✅ 1. Created .gitignore
- Added comprehensive `.gitignore` to exclude:
  - Large data files (`.xlsx`, large `.csv` files)
  - Model files (`.pkl`)
  - Output files
  - Python cache files
  - IDE and OS files

### ✅ 2. Removed large files from staging
- Removed large files from git index using `git rm --cached`
- Files remain on disk but are no longer tracked

### ✅ 3. Renamed remote
- Changed remote from `customer-churn` to `origin` for consistency

### ⚠️ 4. Clean Git History (REQUIRED)

**The large files are still in your git commit history.** You need to remove them before pushing.

#### Option A: Use the provided script (Recommended)
```bash
./clean-git-history.sh
```

#### Option B: Manual cleanup
```bash
# Remove files from all commits
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch data/all-data.xlsx data/train.csv scoring_input.csv chunks/*.csv" \
  --prune-empty --tag-name-filter cat -- --all

# Clean up
git for-each-ref --format="%(refname)" refs/original/ | xargs -n 1 git update-ref -d
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

## Next Steps

1. **Commit the current changes:**
   ```bash
   git add .gitignore
   git commit -m "Add .gitignore and remove large files from tracking"
   ```

2. **Clean git history** (run the script above)

3. **Push to remote:**
   ```bash
   git push -u origin main --force
   ```
   ⚠️ **Warning:** Using `--force` is necessary because we rewrote history. Only do this if you're the only one working on this repo.

## Alternative: Use Git LFS (If you need to track large files)

If you need to version control large files, consider Git LFS:

```bash
# Install git-lfs (if not already installed)
brew install git-lfs  # macOS
# or: apt-get install git-lfs  # Linux

# Initialize git-lfs
git lfs install

# Track large files
git lfs track "*.xlsx"
git lfs track "data/*.csv"
git lfs track "*.pkl"

# Add .gitattributes
git add .gitattributes
```

## Summary

- ✅ `.gitignore` created
- ✅ Large files removed from tracking
- ✅ Remote renamed to `origin`
- ⚠️ **Action Required:** Clean git history before pushing
