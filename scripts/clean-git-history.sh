#!/bin/bash
# Script to remove large files from git history
# WARNING: This rewrites git history. Only run if you haven't pushed successfully yet.

set -e

echo "Removing large files from git history..."
echo "This will rewrite your git history."

# Remove large files from all commits
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch data/all-data.xlsx data/train.csv scoring_input.csv chunks/*.csv" \
  --prune-empty --tag-name-filter cat -- --all

# Clean up refs
git for-each-ref --format="%(refname)" refs/original/ | xargs -n 1 git update-ref -d

# Force garbage collection
git reflog expire --expire=now --all
git gc --prune=now --aggressive

echo "Done! Large files have been removed from git history."
echo "You can now push with: git push -u origin main --force"
