#!/usr/bin/env python3
"""
Quick Start Script for AI Smart Allocation Engine
Launches the web application and provides usage instructions
"""

import subprocess
import sys
import webbrowser
import time
import os

def check_dependencies():
    """Check if required packages are installed"""
    try:
        import flask
        import pandas
        import numpy
        import sklearn
        print("✅ All dependencies are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please run: pip install -r requirements.txt")
        return False

def start_application():
    """Start the Flask web application"""
    print("🚀 Starting AI Smart Allocation Engine...")
    print("=" * 50)
    
    if not check_dependencies():
        return False
    
    print("📱 Web application will be available at: http://localhost:5000")
    print("🌐 Opening browser in 3 seconds...")
    print("⏹️  Press Ctrl+C to stop the server")
    print("=" * 50)
    
    # Wait a moment then open browser
    time.sleep(3)
    try:
        webbrowser.open('http://localhost:5000')
    except e:
        print("Could not open browser automatically. Please visit http://localhost:5000")

    # Start the Flask app
    try:
        subprocess.run([sys.executable, 'app.py'])
    except KeyboardInterrupt:
        print("\n👋 Application stopped. Thank you for using AI Smart Allocation Engine!")
        return True
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        return False

def show_usage_guide():
    """Show usage guide for the application"""
    print("\n📖 Usage Guide:")
    print("-" * 30)
    print("1. Fill out the candidate information form")
    print("2. Include your skills, education, and preferences")
    print("3. Specify any diversity considerations")
    print("4. Click 'Find My Internship Matches'")
    print("5. Review AI-powered recommendations")
    print("6. Apply to internships that interest you")
    print("\n🎯 Features:")
    print("• AI-powered matching algorithm")
    print("• Mobile-responsive design")
    print("• Affirmative action support")
    print("• Regional language support")
    print("• Real-time recommendations")

def main():
    """Main function"""
    print("🎯 AI Smart Allocation Engine - Quick Start")
    print("PM Internship Scheme - Ministry of Corporate Affairs")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not os.path.exists('app.py'):
        print("❌ Please run this script from the project root directory")
        print("   Make sure app.py is in the current directory")
        return
    
    # Show usage guide
    show_usage_guide()
    
    # Start the application
    print("\n🚀 Starting application...")
    start_application()

if __name__ == "__main__":
    main()


