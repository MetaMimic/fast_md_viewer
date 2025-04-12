#!/bin/bash

# Uninstall Fast Markdown Viewer for Linux Mint Cinnamon
# Removes viewer, old Python files, desktop file, and MIME associations

echo "Starting Fast Markdown Viewer uninstallation..."

# --- Check for root privileges ---
if [ "$(id -u)" -ne 0 ]; then
  echo "This script needs to be run with sudo privileges to remove files." >&2
  echo "Please run as: sudo $0" >&2
  exit 1
fi

# --- Remove viewer binaries ---
echo "Removing viewer binaries..."
VIEWER_C="/usr/local/bin/fast_md_viewer"
VIEWER_PY="/usr/local/bin/fast_md_viewer.py"

if [ -f "$VIEWER_C" ]; then
    rm "$VIEWER_C"
    echo "Removed $VIEWER_C"
else
    echo "$VIEWER_C not found, skipping."
fi

if [ -f "$VIEWER_PY" ]; then
    rm "$VIEWER_PY"
    echo "Removed $VIEWER_PY"
else
    echo "$VIEWER_PY not found, skipping."
fi

# --- Remove .desktop file ---
echo "Removing .desktop file..."
DESKTOP_PATH="/usr/share/applications/fast-md-viewer.desktop"
if [ -f "$DESKTOP_PATH" ]; then
    rm "$DESKTOP_PATH"
    echo "Removed $DESKTOP_PATH"
else
    echo "$DESKTOP_PATH not found, skipping."
fi

# --- Remove MIME associations ---
echo "Removing MIME associations..."
if [ -n "$SUDO_USER" ]; then
    USER_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
    MIMEAPPS="$USER_HOME/.config/mimeapps.list"
    if [ -f "$MIMEAPPS" ]; then
        sudo -u "$SUDO_USER" sed -i '/text\/markdown=/d' "$MIMEAPPS"
        sudo -u "$SUDO_USER" sed -i '/text\/x-markdown=/d' "$MIMEAPPS"
        echo "Removed MIME associations from $MIMEAPPS"
    fi
    if [ -d "$USER_HOME/.local/share/applications" ]; then
        sudo -u "$SUDO_USER" update-desktop-database "$USER_HOME/.local/share/applications"
        echo "Updated user desktop database."
    fi
fi

# System-wide MIME cleanup
xdg-mime uninstall "$DESKTOP_PATH" 2>/dev/null
update-desktop-database /usr/share/applications

# --- Optional: Remove dependencies ---
echo "Checking for dependencies to remove (optional)..."
DEPS="libsdl2-dev libsdl2-ttf-dev libcmark-dev python3-mistune gir1.2-webkit2-4.0 gir1.2-webkit2-4.1"
REMOVE_DEPS=""
for pkg in $DEPS; do
    if dpkg -l "$pkg" >/dev/null 2>&1; then
        REMOVE_DEPS="$REMOVE_DEPS $pkg"
    fi
done

if [ -n "$REMOVE_DEPS" ]; then
    echo "Found dependencies: $REMOVE_DEPS"
    read -p "Remove these dependencies? (y/N): " answer
    if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
        apt remove -y $REMOVE_DEPS
        apt autoremove -y
        echo "Dependencies removed."
    else
        echo "Keeping dependencies."
    fi
else
    echo "No dependencies found to remove."
fi

echo ""
echo "Uninstallation complete!"
echo "Fast Markdown Viewer and its associations have been removed."
echo ""
