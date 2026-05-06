#!/bin/bash

# Install script for charcli
set -e

INSTALL_DIR="$HOME/.local/bin"
APP_NAME="charcli"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing $APP_NAME to $INSTALL_DIR..."

# Create install directory if it doesn't exist
mkdir -p "$INSTALL_DIR"

# Copy to charcli-bin folder, preserving user data
if [ -d "$INSTALL_DIR/charcli-bin" ]; then
    echo "Updating existing installation..."
    
    # Backup user data directories
    if [ -d "$INSTALL_DIR/charcli-bin/characters" ]; then
        echo "Preserving existing characters..."
        cp -r "$INSTALL_DIR/charcli-bin/characters" /tmp/charcli_characters_backup_$(date +%s)
    fi
    
    if [ -d "$INSTALL_DIR/charcli-bin/personas" ]; then
        echo "Preserving existing personas..."
        cp -r "$INSTALL_DIR/charcli-bin/personas" /tmp/charcli_personas_backup_$(date +%s)
    fi
    
    if [ -d "$INSTALL_DIR/charcli-bin/chats" ]; then
        echo "Preserving existing chats..."
        cp -r "$INSTALL_DIR/charcli-bin/chats" /tmp/charcli_chats_backup_$(date +%s)
    fi
    
    # Update application files only (exclude user data directories)
    echo "Updating application files..."
    rsync -av --exclude='characters/' --exclude='personas/' --exclude='chats/' --exclude='.git/' --exclude='__pycache__/' "$SOURCE_DIR/" "$INSTALL_DIR/charcli-bin/"
    
    # Restore user data directories
    if [ -d "/tmp/charcli_characters_backup_"* ]; then
        echo "Restoring characters..."
        cp -r /tmp/charcli_characters_backup_* "$INSTALL_DIR/charcli-bin/characters"
        rm -rf /tmp/charcli_characters_backup_*
    fi
    
    if [ -d "/tmp/charcli_personas_backup_"* ]; then
        echo "Restoring personas..."
        cp -r /tmp/charcli_personas_backup_* "$INSTALL_DIR/charcli-bin/personas"
        rm -rf /tmp/charcli_personas_backup_*
    fi
    
    if [ -d "/tmp/charcli_chats_backup_"* ]; then
        echo "Restoring chats..."
        cp -r /tmp/charcli_chats_backup_* "$INSTALL_DIR/charcli-bin/chats"
        rm -rf /tmp/charcli_chats_backup_*
    fi
else
    echo "Installing fresh copy..."
    cp -r "$SOURCE_DIR" "$INSTALL_DIR/charcli-bin"
fi

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
