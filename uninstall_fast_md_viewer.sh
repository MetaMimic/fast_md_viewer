#!/bin/bash

echo "Uninstalling Fast Markdown Viewer..."

# Remove Python viewer
rm -f /usr/local/bin/fast_md_viewer.py

# Remove old C binaries/scripts if present
rm -f /usr/local/bin/fast_md_viewer
rm -f /usr/local/bin/c_install_fast_md_viewer.sh
rm -f /usr/local/bin/c_uninstall_fast_md_viewer.sh

# Remove .desktop file
rm -f /usr/share/applications/fast-md-viewer.desktop

# Remove xdg-mime associations (system-wide and user)
xdg-mime default text-editor.desktop text/markdown
xdg-mime default text-editor.desktop text/x-markdown

# Update desktop databases
update-desktop-database /usr/share/applications

# Remove from user's local applications if present
if [ -n "$SUDO_USER" ]; then
    USER_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
    if [ -d "$USER_HOME/.local/share/applications" ]; then
        sudo -u "$SUDO_USER" rm -f "$USER_HOME/.local/share/applications/fast-md-viewer.desktop"
        sudo -u "$SUDO_USER" update-desktop-database "$USER_HOME/.local/share/applications"
    fi
fi

echo "Uninstall complete. You may need to log out and back in for changes to take effect."