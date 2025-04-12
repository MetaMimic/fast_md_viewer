#!/usr/bin/env python3
import sys
import os

try:
    import gi
    gi.require_version("Gtk", "3.0")
    try:
        gi.require_version("WebKit2", "4.1")
    except ValueError:
        gi.require_version("WebKit2", "4.0")
    from gi.repository import Gtk, WebKit2, Gdk
except ImportError:
    print("Error: python3-gi (PyGObject) and gir1.2-webkit2 are required. Install with 'sudo apt install python3-gi gir1.2-webkit2-4.1' or 'gir1.2-webkit2-4.0'.")
    sys.exit(1)

try:
    import mistune
except ImportError:
    print("Error: mistune is not installed. Please install it with 'sudo apt install python3-mistune'.")
    sys.exit(1)

# Try to import GFM plugin for mistune
try:
    from mistune.plugins import plugin_gfm
except ImportError:
    plugin_gfm = None

import urllib.request
import re

GITHUB_LIGHT_CSS_URL = "https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.5.1/github-markdown-light.min.css"
GITHUB_DARK_CSS_URL = "https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.5.1/github-markdown-dark.min.css"

COPY_ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" style="vertical-align:middle" fill="currentColor" viewBox="0 0 16 16"><path d="M10 1.5A1.5 1.5 0 0 1 11.5 3v1h-1V3a.5.5 0 0 0-.5-.5H3A1.5 1.5 0 0 0 1.5 4v8A1.5 1.5 0 0 0 3 13.5h1v1A1.5 1.5 0 0 0 5.5 16h8a1.5 1.5 0 0 0 1.5-1.5v-8A1.5 1.5 0 0 0 13.5 5H13V3A1.5 1.5 0 0 0 11.5 1.5h-1zm-7 2A.5.5 0 0 1 3 3h7.5a.5.5 0 0 1 .5.5V5h-8V3.5zm1 10A.5.5 0 0 1 3 13V5.5h8V13a.5.5 0 0 1-.5.5H3zm10.5-8A.5.5 0 0 1 14 5.5V15a.5.5 0 0 1-.5.5h-8A.5.5 0 0 1 5 15V5.5h8V3.5z"/></svg>"""

def get_github_css(dark=False):
    url = GITHUB_DARK_CSS_URL if dark else GITHUB_LIGHT_CSS_URL
    try:
        with urllib.request.urlopen(url, timeout=3) as resp:
            css = resp.read().decode("utf-8")
    except Exception:
        # Minimal fallback
        css = """
        .markdown-body { font-family: sans-serif; color: #24292f; background: #fff; padding: 2em; }
        h1, h2, h3, h4, h5, h6 { font-weight: bold; }
        pre, code { background: #f6f8fa; font-family: monospace; }
        """
    # Add 20px margin left/right for readability
    css += ".markdown-body { margin-left:20px; margin-right:20px; margin-top:20px; margin-bottom:20px; }"
    # Style for copy button in code blocks
    css += """
    .copy-btn {
        position: absolute;
        top: 8px;
        right: 8px;
        background: transparent;
        border: none;
        cursor: pointer;
        padding: 0;
        z-index: 10;
        opacity: 0.7;
        transition: opacity 0.2s;
        height: 20px;
        width: 20px;
    }
    .copy-btn:hover { opacity: 1; }
    .code-block-wrapper { position: relative; }
    """
    return css

def inject_copy_buttons(html):
    # Add a wrapper div and copy button to each <pre><code>...</code></pre>
    def repl(match):
        code = match.group(1)
        # Remove leading/trailing newlines for better copying
        code_clean = code.strip('\n')
        btn = f'<button class="copy-btn" onclick="copyCode(this)" title="Copy">{COPY_ICON_SVG}</button>'
        return f'<div class="code-block-wrapper"><pre><code>{code}</code></pre>{btn}</div>'
    # Replace <pre><code>...</code></pre> with wrapper and button
    html = re.sub(r'<pre><code>(.*?)</code></pre>', repl, html, flags=re.DOTALL)
    return html

def render_markdown(md_text, dark=False):
    if plugin_gfm:
        md = mistune.create_markdown(plugins=[plugin_gfm()])
    else:
        md = mistune.create_markdown()
    html = md(md_text)
    html = inject_copy_buttons(html)
    css = get_github_css(dark)
    # JS for copy button (only for this feature)
    js = """
    <script>
    function copyCode(btn) {
        var code = btn.parentElement.querySelector('pre code').innerText;
        navigator.clipboard.writeText(code);
        btn.style.opacity = 1;
        btn.title = "Copied!";
        setTimeout(function() { btn.title = "Copy"; btn.style.opacity = 0.7; }, 1200);
    }
    </script>
    """
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>{css}</style>
</head>
<body class="markdown-body">
{html}
{js}
</body>
</html>
"""

class MarkdownViewer(Gtk.Window):
    def __init__(self, md_path):
        Gtk.Window.__init__(self, title="Fast MD Viewer")
        self.set_default_size(900, 700)
        self.md_path = md_path
        self.dark_mode = False
        self.zoom = 1.0

        # Overlay for button/label
        self.overlay = Gtk.Overlay()
        self.add(self.overlay)

        self.webview = WebKit2.WebView()
        settings = self.webview.get_settings()
        settings.set_enable_javascript(True)  # Needed for copy button
        if hasattr(settings, "set_enable_webgl"):
            settings.set_enable_webgl(False)
        if hasattr(settings, "set_enable_media_stream"):
            settings.set_enable_media_stream(False)
        if hasattr(settings, "set_enable_fullscreen"):
            settings.set_enable_fullscreen(False)
        if hasattr(settings, "set_enable_smooth_scrolling"):
            settings.set_enable_smooth_scrolling(True)
        if hasattr(settings, "set_enable_write_console_messages_to_stdout"):
            settings.set_enable_write_console_messages_to_stdout(False)

        self.overlay.add(self.webview)
        self.load_markdown()

        # Ctrl+scroll for zoom
        self.webview.connect("scroll-event", self.on_scroll)

        # Light/dark mode toggle button
        self.toggle_btn = Gtk.Button()
        self.toggle_btn.set_relief(Gtk.ReliefStyle.NONE)
        self.toggle_btn.set_tooltip_text("Toggle light/dark mode")
        self.toggle_btn.set_size_request(20, 20)
        self.toggle_btn.set_focus_on_click(False)
        self.toggle_btn.set_label("🌙" if not self.dark_mode else "☀️")
        self.toggle_btn.connect("clicked", self.on_toggle_mode)

        # Zoom label
        self.zoom_label = Gtk.Label()
        self.zoom_label.set_margin_start(4)
        self.zoom_label.set_margin_end(2)
        self.zoom_label.set_margin_top(0)
        self.zoom_label.set_margin_bottom(0)
        self.zoom_label.set_halign(Gtk.Align.END)
        self.zoom_label.set_valign(Gtk.Align.END)
        self.zoom_label.set_visible(False)
        self.zoom_label.set_size_request(-1, 28)

        # Box for label and button (label left, button right)
        self.btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        self.btn_box.pack_start(self.zoom_label, False, False, 0)
        self.btn_box.pack_start(self.toggle_btn, False, False, 0)
        self.btn_box.set_halign(Gtk.Align.END)
        self.btn_box.set_valign(Gtk.Align.END)
        self.btn_box.set_margin_end(8)
        self.btn_box.set_margin_bottom(8)
        self.overlay.add_overlay(self.btn_box)
        self.update_zoom_label()

    def load_markdown(self):
        try:
            with open(self.md_path, "r", encoding="utf-8") as f:
                md_text = f.read()
        except Exception as e:
            html = f"<pre>Failed to load file: {e}</pre>"
        else:
            html = render_markdown(md_text, self.dark_mode)
        self.webview.load_html(html, "file://")

    def on_scroll(self, widget, event):
        if event.state & Gdk.ModifierType.CONTROL_MASK:
            cur_zoom = self.webview.get_zoom_level()
            if event.direction == Gdk.ScrollDirection.UP:
                cur_zoom = min(cur_zoom + 0.1, 5.0)
            elif event.direction == Gdk.ScrollDirection.DOWN:
                cur_zoom = max(cur_zoom - 0.1, 0.2)
            self.webview.set_zoom_level(cur_zoom)
            self.zoom = cur_zoom
            self.update_zoom_label()
            return True
        return False

    def on_toggle_mode(self, button):
        self.dark_mode = not self.dark_mode
        self.toggle_btn.set_label("🌙" if not self.dark_mode else "☀️")
        self.update_zoom_label()
        self.load_markdown()

    def update_zoom_label(self):
        percent = int(round(self.zoom * 100))
        if percent != 100:
            self.zoom_label.set_text(f"{percent}%")
            # Toggle color with mode
            if self.dark_mode:
                self.zoom_label.set_markup(f'<span foreground="#eee" size="large">{percent}%</span>')
            else:
                self.zoom_label.set_markup(f'<span foreground="#222" size="large">{percent}%</span>')
            self.zoom_label.set_visible(True)
        else:
            self.zoom_label.set_visible(False)

def main():
    if len(sys.argv) < 2 or not os.path.isfile(sys.argv[1]):
        print("Usage: fast_md_viewer.py <file.md>")
        sys.exit(1)
    win = MarkdownViewer(sys.argv[1])
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    main()