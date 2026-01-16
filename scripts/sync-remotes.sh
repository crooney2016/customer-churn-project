#!/bin/bash
# Sync Git repository to both GitHub and Azure DevOps remotes
#
# Usage:
#   ./scripts/sync-remotes.sh [branch-name]
#   Default branch: main

BRANCH=${1:-main}

echo "Syncing branch '$BRANCH' to both remotes..."

# Fetch latest from both remotes
echo "Fetching from GitHub..."
git fetch github

echo "Fetching from Azure DevOps..."
git fetch azure

# Push to GitHub
echo "Pushing to GitHub (origin)..."
if git push github "$BRANCH"; then
    echo "✅ Successfully pushed to GitHub"
else
    echo "❌ Failed to push to GitHub"
    exit 1
fi

# Push to Azure DevOps
echo "Pushing to Azure DevOps..."
if git push azure "$BRANCH"; then
    echo "✅ Successfully pushed to Azure DevOps"
else
    echo "❌ Failed to push to Azure DevOps"
    exit 1
fi

echo ""
echo "✅ Successfully synced to both remotes!"
echo "  - GitHub: $(git remote get-url github)"
echo "  - Azure DevOps: $(git remote get-url azure)"
