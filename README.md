# Fast Markdown Viewer (Python)

A lightning-fast, minimal Markdown viewer for Linux Mint Cinnamon and other GTK-based desktops. Double-click `.md` files to view them instantly in a clean, resizable window with crisp scrolling and zoom.

## Features

- **Instant startup**: Launches in ~20-30ms on modern hardware.
- **Crisp, fast scrolling**: Uses GTK WebKit2 for smooth rendering.
- **Ctrl+Scroll to Zoom**: Hold Ctrl and scroll to zoom in/out in 10% steps.
- **Dark-on-light theme**: Uses your system's default theme for readability.
- **No unnecessary dependencies**: Only Python 3, Mistune, and WebKit2GTK.

## Installation

1. **Run the installer** (as root/sudo):

   ```bash
   sudo ./install_fast_md_viewer.sh
   ```

   This will:
   - Install required dependencies (`python3-mistune`, `gir1.2-webkit2-4.1` or `gir1.2-webkit2-4.0`)
   - Copy `fast_md_viewer.py` to `/usr/local/bin/`
   - Register the viewer as the default app for `.md` files

2. **(Optional)**: You can run the Python script directly for testing:

   ```bash
   ./fast_md_viewer.py README.md
   ```

## Usage

- **Double-click** any `.md` file in your file manager, or run:

  ```bash
  fast_md_viewer.py yourfile.md
  ```

- **Zoom**: Hold `Ctrl` and scroll up/down to zoom in/out (10% steps).

## Dependencies

- Python 3
- [Mistune](https://github.com/lepture/mistune) (`python3-mistune`)
- GTK 3 (`gir1.2-gtk-3.0`)
- WebKit2GTK (`gir1.2-webkit2-4.1` or `gir1.2-webkit2-4.0`)

Install with:

```bash
sudo apt install python3-mistune gir1.2-webkit2-4.1 || sudo apt install gir1.2-webkit2-4.0
```

## Troubleshooting

- If you see errors about missing `WebKit2` or `mistune`, install the dependencies above.
- If double-clicking `.md` files doesn't work, try logging out and back in, or check your default application settings.

## Uninstall

Run the provided uninstall script:

```bash
sudo ./uninstall_fast_md_viewer.sh
```

## License

MIT License. See source for details.