#!/usr/bin/env python3
"""
Browser History Viewer - Startup Script
Run this file to start the application with proper directory setup
"""

import os
import sys
from pathlib import Path

def create_directory_structure():
    """Create necessary directories if they don't exist"""
    base_dir = Path(__file__).parent
    
    # Create templates directory
    templates_dir = base_dir / "templates"
    templates_dir.mkdir(exist_ok=True)
    
    # Create static directory
    static_dir = base_dir / "static"
    static_dir.mkdir(exist_ok=True)
    
    # Check if index.html exists in templates
    index_path = templates_dir / "index.html"
    if not index_path.exists():
        print("⚠️  Warning: templates/index.html not found!")
        print("Please save the HTML template as 'templates/index.html'")
        return False
    
    return True

def check_requirements():
    """Check if required packages are installed"""
    try:
        import flask
        import werkzeug
        return True
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("Please install requirements with: pip install Flask Werkzeug")
        return False

def main():
    print("🌐 Browser History Viewer")
    print("=" * 50)
    
    # Check requirements
    if not check_requirements():
        return
    
    # Create directory structure
    if not create_directory_structure():
        return
    
    # Import and run the main application
    try:
        from app import app
        print("✅ Application loaded successfully!")
        print("🚀 Starting server...")
        print("📂 Upload your browser database files at: http://localhost:5000")
        print("⏹️  Press Ctrl+C to stop the server")
        print("-" * 50)
        
        app.run(debug=True, host='0.0.0.0', port=5000)
        
    except ImportError:
        print("❌ Could not import app.py")
        print("Please ensure app.py is in the same directory as this script")
    except Exception as e:
        print(f"❌ Error starting application: {e}")

if __name__ == "__main__":
    main()