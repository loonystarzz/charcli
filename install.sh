#!/bin/bash

# Install script for charcli
set -e

INSTALL_DIR="$HOME/.local/bin"
APP_NAME="charcli"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing $APP_NAME to $INSTALL_DIR..."

# Create install directory if it doesn't exist
mkdir -p "$INSTALL_DIR"

# Copy to charcli-bin folder (not app name folder)
if [ -d "$INSTALL_DIR/$APP_NAME" ]; then
    echo "Removing existing installation..."
    rm -rf "$INSTALL_DIR/$APP_NAME"
fi

echo "Copying files to $INSTALL_DIR/charcli-bin..."
cp -r "$SOURCE_DIR" "$INSTALL_DIR/charcli-bin"

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --break-system-packages -r "$INSTALL_DIR/charcli-bin/requirements.txt"

# Create a symlink to the run script
echo "Creating symlink..."
ln -sf "$INSTALL_DIR/charcli-bin/run" "$INSTALL_DIR/$APP_NAME"

# Make run script executable
chmod +x "$INSTALL_DIR/charcli-bin/run"

# Add ~/.local/bin to PATH if not already there
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    echo "Adding $INSTALL_DIR to PATH..."
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc" 2>/dev/null || true
fi

echo ""
echo "Installation complete!"
echo ""
echo "To use charcli:"
echo "1. Restart your terminal or run: source ~/.bashrc (or ~/.zshrc)"
echo "2. Then run: charcli"
echo ""
echo "The app is installed at: $INSTALL_DIR/charcli-bin"
