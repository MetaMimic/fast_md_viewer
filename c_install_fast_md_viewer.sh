#!/bin/bash

# Fast Markdown Viewer Installer for Linux Mint Cinnamon
# Installs dependencies, compiles C viewer, and associates .md files

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
    echo "Error: Failed to update package lists. Check your connection and apt sources." >&2
    exit 1
fi

echo "Installing dependencies (SDL2, SDL2_ttf, cmark, gcc, fonts-dejavu)..."
for pkg in libsdl2-dev libsdl2-ttf-dev libcmark-dev gcc fonts-dejavu; do
    echo "Installing $pkg..."
    apt install -y "$pkg"
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install $pkg." >&2
        exit 1
    fi
    dpkg -l "$pkg" >/dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "Error: $pkg installed but not detected." >&2
        exit 1
    fi
done
echo "Dependencies installed successfully."

# --- Verify pkg-config for libraries ---
echo "Verifying pkg-config for sdl2, SDL2_ttf, cmark..."
for lib in sdl2 SDL2_ttf; do
    pkg-config --modversion "$lib" >/dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "Error: pkg-config cannot find $lib." >&2
        echo "Ensure $lib.pc is in /usr/lib/x86_64-linux-gnu/pkgconfig or similar." >&2
        exit 1
    fi
done
# Check cmark separately
CMARK_FLAGS=""
pkg-config --modversion cmark >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Warning: pkg-config cannot find cmark.pc. Using fallback flags." >&2
    CMARK_FLAGS="-I/usr/include -L/usr/lib -lcmark"
else
    CMARK_FLAGS="$(pkg-config --cflags --libs cmark)"
fi
echo "pkg-config verification complete."

# --- Compile C program ---
echo "Compiling fast_md_viewer.c..."
VIEWER_SRC="fast_md_viewer.c"
VIEWER_BIN="/usr/local/bin/fast_md_viewer"

if [ ! -f "$VIEWER_SRC" ]; then
    echo "Error: $VIEWER_SRC not found in current directory." >&2
    echo "Please place $VIEWER_SRC in the same directory as this script." >&2
    exit 1
fi

gcc "$VIEWER_SRC" -o "$VIEWER_BIN" $(pkg-config --cflags --libs sdl2 SDL2_ttf) $CMARK_FLAGS -O2
if [ $? -ne 0 ]; then
    echo "Error: Compilation failed." >&2
    exit 1
fi
chmod +x "$VIEWER_BIN"
echo "Viewer binary created at $VIEWER_BIN"

# --- Create .desktop file ---
echo "Creating .desktop file..."
DESKTOP_DIR="/usr/share/applications"
DESKTOP_PATH="$DESKTOP_DIR/fast-md-viewer.desktop"
mkdir -p "$DESKTOP_DIR"

cat > "$DESKTOP_PATH" << EOF
[Desktop Entry]
Name=Fast Markdown Viewer
Comment=View Markdown files
Exec=$VIEWER_BIN %f
Type=Application
Terminal=false
Icon=text-x-generic
Categories=Utility;Viewer;
MimeType=text/markdown;text/x-markdown;
EOF
if [ $? -ne 0 ]; then
    echo "Error: Failed to create .desktop file." >&2
    exit 1
fi
echo ".desktop file created at $DESKTOP_PATH"

# --- Associate .md files ---
echo "Setting file associations..."
update-desktop-database "$DESKTOP_DIR"
xdg-mime default fast-md-viewer.desktop text/markdown
xdg-mime default fast-md-viewer.desktop text/x-markdown
if [ $? -ne 0 ]; then
    echo "Error: Failed to set MIME associations." >&2
    exit 1
fi

# Update user-specific MIME settings if run via sudo
if [ -n "$SUDO_USER" ]; then
    USER_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
    if [ -d "$USER_HOME/.local/share/applications" ]; then
        sudo -u "$SUDO_USER" update-desktop-database "$USER_HOME/.local/share/applications"
        sudo -u "$SUDO_USER" xdg-mime default fast-md-viewer.desktop text/markdown
        sudo -u "$SUDO_USER" xdg-mime default fast-md-viewer.desktop text/x-markdown
        echo "User MIME settings updated for $SUDO_USER."
    fi
fi

echo ""
echo "Installation complete!"
echo "Double-click .md files to open with Fast Markdown Viewer."
echo "Verify with: xdg-mime query default text/markdown"
echo "To uninstall, run: sudo bash uninstall_fast_md_viewer.sh"
echo ""
exit 0
