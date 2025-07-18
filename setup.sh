#!/bin/bash

# Discord Yoink - Quick Setup Script
# This script sets up the Discord Yoink project on Unix-like systems

echo "Discord Yoink - Setup Script"
echo "============================="

# Check if Python 3.8+ is available
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
elif command -v python &> /dev/null; then
    PYTHON_CMD=python
else
    echo "Error: Python is not installed or not in PATH"
    exit 1
fi

# Check Python version
echo "Checking Python version..."
$PYTHON_CMD -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"
if [ $? -ne 0 ]; then
    echo "Error: Python 3.8 or higher is required"
    exit 1
fi

echo "✓ Python version check passed"

# Create virtual environment (optional but recommended)
read -p "Create virtual environment? [y/N]: " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Creating virtual environment..."
    $PYTHON_CMD -m venv venv
    
    # Activate virtual environment
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        echo "✓ Virtual environment created and activated"
    else
        echo "Warning: Could not activate virtual environment"
    fi
fi

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✓ Dependencies installed successfully"
else
    echo "Error: Failed to install dependencies"
    exit 1
fi

# Run setup script
echo "Running setup script..."
$PYTHON_CMD project_setup.py

echo ""
echo "Setup complete! You can now use Discord Yoink."
echo ""
echo "If you created a virtual environment, remember to activate it:"
echo "source venv/bin/activate"
