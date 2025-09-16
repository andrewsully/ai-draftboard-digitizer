#!/usr/bin/env python3
"""
Main entry point for the Fantasy Football Draft Board OCR application.
Launches the web interface from the scripts directory.
"""

import os
import sys
import subprocess

def main():
    """Launch the Flask web application."""
    # Change to the scripts directory and run the app
    script_path = os.path.join(os.path.dirname(__file__), 'scripts', 'app.py')
    
    if not os.path.exists(script_path):
        print("❌ Error: Application script not found at scripts/app.py")
        sys.exit(1)
    
    print("🏈 Launching Fantasy Football Draft Board OCR...")
    print("📱 Web interface will be available at: http://localhost:5001")
    
    # Execute the script in the scripts directory
    os.chdir(os.path.join(os.path.dirname(__file__), 'scripts'))
    subprocess.run([sys.executable, 'app.py'])

if __name__ == '__main__':
    main()
