#!/usr/bin/env bash
# Build script for Render deployment

set -o errexit  # exit on error

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install system dependencies (FFmpeg)
apt-get update
apt-get install -y ffmpeg

echo "Build completed successfully!"