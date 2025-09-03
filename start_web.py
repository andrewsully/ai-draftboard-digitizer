#!/usr/bin/env python3
"""
Startup script for the Fantasy Football Draft Board OCR Web Interface
"""

import os
import sys
import webbrowser
import time
from threading import Timer

def open_browser():
    """Open the web browser to the application"""
    webbrowser.open('http://localhost:5001')

if __name__ == '__main__':
    print("🏈 Starting Fantasy Football Draft Board OCR Web Interface...")
    print("=" * 60)
    
    # Check if required files exist
    required_files = [
        'data/top500_playernames.csv',
        'src/preprocess.py',
        'src/grid.py',
        'src/ocr_cell.py',
        'src/reconcile.py',
        'src/emit.py'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print("❌ Missing required files:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        print("\nPlease ensure all required files are present.")
        sys.exit(1)
    
    print("✅ All required files found!")
    print("🌐 Starting web server on http://localhost:5001")
    print("📱 Opening browser in 3 seconds...")
    
    # Open browser after 3 seconds
    Timer(3.0, open_browser).start()
    
    # Start the Flask app
    from app import app
    app.run(debug=False, host='0.0.0.0', port=5001)
