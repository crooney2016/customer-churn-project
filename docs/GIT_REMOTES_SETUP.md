# Git Dual Remote Setup Guide

**Project:** Century Churn Prediction System
**Last Updated:** 2024-12-19
**Version:** 1.0

## Overview

This guide explains how to configure and use two Git remotes for this project:

- **GitHub** (for AI tools like Claude and Codex)
- **Azure DevOps** (for Microsoft shop deployment pipelines)

## Why Dual Remotes

- **GitHub:** Provides easy access for AI tools (Claude, Codex) that work well with GitHub repositories
- **Azure DevOps:** Native Microsoft integration, preferred for enterprise deployment pipelines
- **Flexibility:** Keep code accessible to AI tools while maintaining Microsoft-centric deployment

## Setup Instructions

### Step 1: Add Azure DevOps Remote

First, create or identify your Azure DevOps repository URL:

```bash
# Add Azure DevOps as second remote (rename existing if needed)
git remote rename origin github

# Add Azure DevOps remote
git remote add azure [https://dev.azure.com/](https://dev.azure.com/)<organization>/<project>/_git/<repository>

# Verify remotes
git remote -v
```

## Expected output

```text
azure   [https://dev.azure.com/org/project/_git/repo](https://dev.azure.com/org/project/_git/repo) (fetch)
azure   [https://dev.azure.com/org/project/_git/repo](https://dev.azure.com/org/project/_git/repo) (push)
github  [https://github.com/user/repo.git](https://github.com/user/repo.git) (fetch)
github  [https://github.com/user/repo.git](https://github.com/user/repo.git) (push)
```

### Step 2: Set Push Defaults

Configure Git to push to both remotes by default:

```bash
# Option 1: Push to both remotes manually (recommended)
# Use sync script (see below)

# Option 2: Configure push URL for origin (if you keep origin)
# git remote set-url --add --push origin [https://github.com/user/repo.git](https://github.com/user/repo.git)
# git remote set-url --add --push origin [https://dev.azure.com/org/project/_git/repo](https://dev.azure.com/org/project/_git/repo)
```

**Recommendation:** Use the sync script for explicit control over which remote gets pushed to.

## Step 3: Initial Push to Azure DevOps

Push your current branch to Azure DevOps:

```bash
# Push main branch to Azure DevOps
git push azure main

# Or set upstream tracking
git push -u azure main
```

## Manual Sync

### Push to GitHub only

```bash
git push github main
```

#### Push to Azure DevOps only

```bash
git push azure main
```

#### Push to both remotes

```bash
# Use the sync script (recommended)
./scripts/sync-remotes.sh main

# Or manually push to both
git push github main && git push azure main
```

## Automated Sync Script

### Make script executable

```bash
chmod +x scripts/sync-remotes.sh
```

```bash
# Sync main branch to both remotes
./scripts/sync-remotes.sh

# Sync specific branch
./scripts/sync-remotes.sh develop
```

## Git Hook (Optional)

Create a post-push hook to automatically sync to both remotes:

```bash
# Create post-push hook
cat > .git/hooks/post-push << 'EOF'
#!/bin/bash
BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$BRANCH" = "main" ]; then
    echo "Syncing to Azure DevOps..."
    git push azure main |  | true
fi
EOF

chmod +x .git/hooks/post-push
```

**Note:** Git hooks are not committed to the repository. Each developer needs to set this up locally if desired.

## Common Workflows

### Daily Development

```bash
# Work on feature branch
git checkout -b feature/new-feature

# Make changes and commit
git add .
git commit -m "Add new feature"

# Push to GitHub (for AI tools access)
git push github feature/new-feature

# Create PR on GitHub
# After PR merge, sync main to both remotes
```

## After Merging to Main

```bash
# Pull latest from GitHub (after PR merge)
git checkout main
git pull github main

# Sync to both remotes
./scripts/sync-remotes.sh main
```

## Branch Management

```bash
# Fetch from both remotes
git fetch github
git fetch azure

# Check branch status
git status

# See commits unique to each remote
git log github/main..azure/main  # Commits in GitHub not in Azure DevOps
git log azure/main..github/main  # Commits in Azure DevOps not in GitHub
```

## Troubleshooting

### Remote Already Exists

If you already have remotes configured:

```bash
# List current remotes
git remote -v

# Rename existing origin to github
git remote rename origin github

# Add Azure DevOps as new remote
git remote add azure <azure-devops-url>
```

## Authentication Issues

### GitHub Authentication

```bash
# Use Personal Access Token
git remote set-url github https://<token>@github.com/user/repo.git

# Or use SSH
git remote set-url github git@github.com:user/repo.git
```

## Azure DevOps Authentication

```bash
# Use Personal Access Token 2
git remote set-url azure https://<token>@dev.azure.com/org/project/_git/repo

# Or use SSH 2
git remote set-url azure git@ssh.dev.azure.com:v3/org/project/repo
```

## Sync Conflicts

If branches diverge:

```bash
# Fetch from both
git fetch github
git fetch azure

# See differences
git log --oneline --graph --all --decorate

# Rebase or merge as needed
git checkout main
git pull github main
git push azure main
```

## CI/CD Considerations

### GitHub Actions

GitHub Actions will trigger on pushes to the `github` remote:

- `.github/workflows/ci.yml` - Runs on push to `github/main`
- `.github/workflows/deploy.yml` - Runs on push to `github/main`

### Azure DevOps Pipelines

Azure DevOps pipelines will trigger on pushes to the `azure` remote:

- `azure-pipelines.yml` - Runs on push to `azure/main`

**Note:** You can disable GitHub Actions for Azure DevOps pushes by using path filters or excluding specific remotes.

## Best Practices

1. **Use sync script:** Use `sync-remotes.sh` for consistent syncing
1. **Keep main in sync:** Always sync `main` branch to both remotes
1. **Feature branches:** Push feature branches to GitHub for AI tools access
1. **Deployment branches:** Use Azure DevOps for deployment pipelines
1. **Document changes:** Update this guide if workflow changes

## Repository Structure

```text
century-churn-prediction-project/
├── .github/
│   └── workflows/          # GitHub Actions (CI/CD for GitHub remote)
│       ├── ci.yml
│       └── deploy.yml
├── azure-pipelines.yml     # Azure DevOps Pipeline (CI/CD for Azure remote)
├── scripts/
│   └── sync-remotes.sh    # Script to sync both remotes
└── docs/
    └── GIT_REMOTES_SETUP.md  # This file
```

## Security Considerations

1. **Separate credentials:** Use different Personal Access Tokens for GitHub and Azure DevOps
1. **Branch protection:** Enable branch protection on both remotes
1. **Access control:** Limit who can push to each remote
1. **Audit logs:** Monitor push activity on both platforms

## References

- [Git Remotes Documentation](https://git-scm.com/book/en/v2/Git-Basics-Working-with-Remotes)
- [Azure DevOps Git Setup](https://learn.microsoft.com/azure/devops/repos/git/)
- [GitHub Actions Documentation](https://docs.github.com/actions)
- [Azure Pipelines Documentation](https://learn.microsoft.com/azure/devops/pipelines/)
