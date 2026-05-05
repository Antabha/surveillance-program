#!/bin/bash

# Define variables
PROJECT_ID="{{YOUR_PROJECT_ID}}"
PLACEHOLDER="{{YOUR_PROJECT_ID}}"
EXPORT_DIR="/tmp/public_export_$(date +%s)"

echo "Starting Public Export..."

# 1. Clone current directory into temporary folder
echo "Cloning files to $EXPORT_DIR..."
mkdir -p "$EXPORT_DIR"
cp -r . "$EXPORT_DIR"

# Navigate to the temp directory
cd "$EXPORT_DIR" || exit

# 2. Erase private commit history
echo "Erasing private commit history..."
rm -rf .git

# 3. Delete all files listed in .gitignore
echo "Removing ignored files (e.g. .venv, .exe, .wav)..."
# We temporarily initialize a git repo just to leverage 'git clean'
git init --quiet
# -f = force, -d = directories, -X = ONLY files ignored by .gitignore
git clean -fdX --quiet

# 4. Search and Replace GCP Project ID
echo "Anonymizing GCP Project ID..."
# Find all files (ignoring the .git directory we just made) and replace the string
find . -type f ! -path "*/.git/*" -exec sed -i "s/$PROJECT_ID/$PLACEHOLDER/g" {} + 2>/dev/null

# 5. Initialize fresh git repository
echo "Initializing fresh git repository..."
git add .
git commit -m "Initial public release" --quiet

echo "====================================================="
echo "✅ Public export successfully created!"
echo "📂 Location: $EXPORT_DIR"
echo "====================================================="
