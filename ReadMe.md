## 9. README.md - Documentation
# Figma to DigitalOcean Spaces

A Python project that extracts images and metadata from Figma files and uploads them to DigitalOcean Spaces.

## Features

- Extract images and JSON metadata from Figma files
- Download images locally as intermediate step
- Upload images to DigitalOcean Spaces with proper organization
- Support for both full file extraction and selective page/frame extraction
- Environment variable configuration for security
- Comprehensive logging and error handling
- Clean, modular codebase

## Installation

### 1. Clone/Create the Project Directory
```bash
mkdir figma-to-digitalocean
cd figma-to-digitalocean
```

### 2. Create Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
# Make sure virtual environment is activated (you should see (venv) in your prompt)
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your actual credentials
# Use your preferred text editor (nano, vim, code, etc.)
nano .env
```

### 5. Verify Installation
```bash
# Test that all dependencies are installed correctly
python -c "import requests, boto3, dotenv; print('All dependencies installed successfully!')"
```

### 6. Deactivate Virtual Environment (when done)
```bash
deactivate
```

## Usage

### Basic Usage (Interactive Mode - Recommended)
```bash
# Activate virtual environment first
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate     # Windows

# Run with interactive prompts
python main.py

# Run with some pre-configured options
python main.py --remote-folder "my-designs" --cleanup
```

### Advanced Usage (Command Line Mode)
```bash
# Non-interactive mode (requires file-key)
python main.py --no-interactive --file-key YOUR_FIGMA_FILE_KEY --document-name "My Design"

# Selective extraction with custom remote folder
python main.py --file-key YOUR_FIGMA_FILE_KEY --selective --remote-folder "designs/v2" --cleanup

# Skip upload (local download only)
python main.py --file-key YOUR_FIGMA_FILE_KEY --skip-upload
```

## Configuration

Set these environment variables in your `.env` file:

- `FIGMA_API_TOKEN`: Your Figma personal access token
- `DO_ACCESS_KEY`: DigitalOcean Spaces access key
- `DO_SECRET_KEY`: DigitalOcean Spaces secret key
- `DO_REGION`: DigitalOcean region (e.g., 'nyc3')
- `DO_SPACE_NAME`: Your DigitalOcean Space name

## Project Structure

```
figma-to-digitalocean/
├── main.py                 # Entry point and orchestration
├── src/
│   ├── config.py          # Configuration management
│   ├── figma_extractor.py # Figma API integration
│   ├── digitalocean_uploader.py # DigitalOcean Spaces integration
│   └── utils.py           # Utility functions
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── setup.py              # Package setup
└── README.md             # This file
```

## 10. setup.sh - Quick setup script (Unix/macOS/Linux)
#!/bin/bash

echo "🚀 Setting up Figma to DigitalOcean project..."

# Check if Python is installed
if ! command -v python &> /dev/null; then
    echo "❌ Python is not installed. Please install Python 3.7+ first."
    exit 1
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
python -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Copy environment template
if [ ! -f .env ]; then
    echo "📋 Creating .env file from template..."
    cp .env.example .env
    echo "✏️  Please edit .env file with your actual credentials:"
    echo "   - FIGMA_API_TOKEN"
    echo "   - DO_ACCESS_KEY"
    echo "   - DO_SECRET_KEY"
    echo "   - DO_REGION"
    echo "   - DO_SPACE_NAME"
else
    echo "✅ .env file already exists"
fi

# Test installation
echo "🧪 Testing installation..."
python -c "import requests, boto3, dotenv; print('✅ All dependencies installed successfully!')" 2>/dev/null

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Setup completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Edit .env file with your credentials"
    echo "2. Run: python main.py --file-key YOUR_FIGMA_FILE_KEY --document-name 'My Design'"
    echo ""
    echo "To activate the virtual environment in the future, run:"
    echo "source venv/bin/activate"
else
    echo "❌ Installation test failed. Please check for errors above."
fi


## 11. setup.bat - Quick setup script (Windows)
@echo off
echo 🚀 Setting up Figma to DigitalOcean project...

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed. Please install Python 3.7+ first.
    pause
    exit /b 1
)

REM Create virtual environment
echo 📦 Creating virtual environment...
python -m venv venv

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo ⬆️ Upgrading pip...
pip install --upgrade pip

REM Install requirements
echo 📥 Installing dependencies...
pip install -r requirements.txt

REM Copy environment template
if not exist .env (
    echo 📋 Creating .env file from template...
    copy .env.example .env
    echo ✏️ Please edit .env file with your actual credentials:
    echo    - FIGMA_API_TOKEN
    echo    - DO_ACCESS_KEY
    echo    - DO_SECRET_KEY
    echo    - DO_REGION
    echo    - DO_SPACE_NAME
) else (
    echo ✅ .env file already exists
)

REM Test installation
echo 🧪 Testing installation...
python -c "import requests, boto3, dotenv; print('✅ All dependencies installed successfully!')" 2>nul

if %errorlevel% equ 0 (
    echo.
    echo 🎉 Setup completed successfully!
    echo.
    echo Next steps:
    echo 1. Edit .env file with your credentials
    echo 2. Run: python main.py --file-key YOUR_FIGMA_FILE_KEY --document-name "My Design"
    echo.
    echo To activate the virtual environment in the future, run:
    echo venv\Scripts\activate.bat
) else (
    echo ❌ Installation test failed. Please check for errors above.
)

pause