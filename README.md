# Fast MD Viewer

A lightweight, fast, and minimal Markdown viewer for Linux, using Python, GTK, and WebKit2.  
Designed for speed, simplicity, and a native look—no Electron, no bloat.

## Features

- **Instant rendering** of Markdown files with GitHub-style CSS
- **Dark/Light mode toggle** with reliable scroll position preservation
- **Zoom** in/out with Ctrl+Scroll
- **Automatic scroll restoration** (even after toggling modes)
- **Minimal dependencies** (Python 3, PyGObject, WebKit2GTK, Mistune)
- **Tested on Linux Mint 22.1 Cinnamon**

## Installation

Use the provided install script for easy setup:

```sh
./install_fast_md_viewer.sh
```

Or, for the C version (in progress):

```sh
cd c
./c_install_fast_md_viewer.sh
```

## Usage

```sh
./fast_md_viewer.py path/to/file.md
```

- Toggle dark/light mode with the button in the bottom right.
- Zoom in/out with Ctrl + mouse scroll.
- Scroll position is preserved when toggling modes.

## Requirements

- Python 3
- PyGObject (`python3-gi`)
- WebKit2GTK (`gir1.2-webkit2-4.1` or `gir1.2-webkit2-4.0`)
- Mistune (`python3-mistune`)

Install dependencies on Debian/Ubuntu/Mint:

```sh
sudo apt install python3-gi gir1.2-webkit2-4.1 python3-mistune
```

## Notes

- The C version is planned for even greater speed and minimalism.
- For issues or suggestions, please open an issue or PR.