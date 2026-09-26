#!/usr/bin/env bash
# Build script for Render

# 1. Build the React frontend
cd frontend
npm install
npm run build
cd ..

# 2. Install Python dependencies
cd backend
pip install -r requirements.txt
cd ..
