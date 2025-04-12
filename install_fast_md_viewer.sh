#!/bin/bash

# Fast Markdown Viewer Installer for Linux Mint Cinnamon
# Installs dependencies, sets up viewer, and associates .md files

echo "Starting Fast Markdown Viewer installation..."

# --- Check for root privileges ---
if [ "$(id -u)" -ne 0 ]; then
  echo "This script needs to be run with sudo privileges to install packages and place files." >&2
  echo "Please run as: sudo $0" >&2
  exit 1
fi

# --- Install dependencies ---
echo "Updating package lists..."
apt update
if [ $? -ne 0 ]; then
    echo "Error: Failed to update package lists. Please check your connection and apt sources."
    exit 1
fi

echo "Installing dependencies (python3-gi and python3-mistune)..."
apt install -y python3-gi python3-mistune
if [ $? -ne 0 ]; then
    echo "Error: Failed to install dependencies (python3-gi, python3-mistune)."
    exit 1
fi
echo "Dependencies installed successfully."

# --- Create viewer program ---
echo "Creating viewer program..."
VIEWER_PATH="/usr/local/bin/fast_md_viewer.py"

# Use tee with sudo privileges (already checked we have them)
# Copy Python viewer from project directory
cp "$(dirname "$0")/fast_md_viewer.py" "$VIEWER_PATH"
chmod +x "$VIEWER_PATH"
echo "Viewer script copied to $VIEWER_PATH"

# --- Create .desktop file ---
# This file needs to be accessible by the user's desktop environment
# Placing it in /usr/share/applications makes it system-wide
# Placing it in ~/.local/share/applications makes it user-specific
# Let's go system-wide as we installed the binary system-wide.
echo "Creating .desktop file..."
DESKTOP_DIR="/usr/share/applications"
DESKTOP_PATH="$DESKTOP_DIR/fast-md-viewer.desktop"
mkdir -p "$DESKTOP_DIR" # Ensure directory exists

# Use tee with sudo for system-wide path
tee "$DESKTOP_PATH" > /dev/null << EOF
[Desktop Entry]
Name=Fast Markdown Viewer
Comment=View Markdown files
# Use the actual path to the executable script
Exec=$VIEWER_PATH %f
Type=Application
Terminal=false
# Add standard icon and categories
Icon=text-x-generic
Categories=Utility;Viewer;TextEditor;
# Register for common Markdown MIME types
MimeType=text/markdown;text/x-markdown;
EOF
echo ".desktop file created at $DESKTOP_PATH"

# --- Associate .md files using xdg-mime (preferred method) ---
# This modifies user-specific settings (~/.config/mimeapps.list usually)
# Run xdg-mime commands as the user who ran sudo, if possible, or rely on system-wide update
# Getting the original user is tricky; let's just update system-wide and user databases

echo "Setting file associations using xdg-mime..."
# Update system-wide database first
update-desktop-database "$DESKTOP_DIR"

# Set default for the MIME types
xdg-mime default fast-md-viewer.desktop text/markdown
xdg-mime default fast-md-viewer.desktop text/x-markdown

echo "Attempting to update user's desktop database (might require user interaction or relogin)..."
# Try updating the user's local database too, if SUDO_USER is set
if [ -n "$SUDO_USER" ]; then
    USER_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
    if [ -d "$USER_HOME/.local/share/applications" ]; then
        sudo -u "$SUDO_USER" update-desktop-database "$USER_HOME/.local/share/applications"
        echo "User database updated for $SUDO_USER."
    else
        echo "User local applications directory not found for $SUDO_USER."
    fi
    # Also run xdg-mime as the user to ensure ~/.config/mimeapps.list is updated
    sudo -u "$SUDO_USER" xdg-mime default fast-md-viewer.desktop text/markdown
    sudo -u "$SUDO_USER" xdg-mime default fast-md-viewer.desktop text/x-markdown
else
    echo "Could not determine original user (SUDO_USER not set). User might need to manually set default or relogin."
fi

# --- Final Check (Optional) ---
# Note: Running xdg-mime query as root might show root's defaults, not the user's
echo ""
echo "Installation complete!"
echo "Double-clicking .md files should now open with Fast Markdown Viewer."
echo "A system restart or re-login might be required for changes to fully apply."
echo ""
echo "To check the default application for markdown:"
echo "  xdg-mime query default text/markdown"
echo "  xdg-mime query default text/x-markdown"
echo "(Run this command as your normal user, not as root/sudo)"
echo ""