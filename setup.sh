#!/usr/bin/env bash
# TinyBrain Python Setup Script

set -e

echo "🧠 TinyBrain Python Setup"
echo "========================="
echo ""

# Check if UV is installed
if ! command -v uv &> /dev/null; then
    echo "📦 UV not found. Installing UV..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo "✓ UV installed"
else
    echo "✓ UV already installed"
fi

# Check if mise is installed (optional)
if ! command -v mise &> /dev/null; then
    echo "⚠️  mise not found (optional). Install with: curl https://mise.run | sh"
else
    echo "✓ mise already installed"
    echo "📦 Installing Python version with mise..."
    mise install
fi

# Create virtual environment and install dependencies
echo ""
echo "📦 Installing dependencies..."
uv sync

# Activate virtual environment message
echo ""
echo "✓ Dependencies installed"
echo ""
echo "📝 Next steps:"
echo "  1. Activate virtual environment:"
echo "     source .venv/bin/activate"
echo ""
echo "  2. Install package in development mode:"
echo "     uv pip install -e ."
echo ""
echo "  3. Initialize database:"
echo "     tinybrain init"
echo ""
echo "  4. Start server:"
echo "     tinybrain serve"
echo ""
echo "For more information, see QUICKSTART.md"
echo ""
echo "Happy hacking! 🧠🔒"
