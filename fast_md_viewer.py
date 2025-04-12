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
    from gi.repository import Gtk, WebKit2, Gdk, GLib
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

GITHUB_LIGHT_CSS_URL = "https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.5.1/github-markdown-light.min.css"
GITHUB_DARK_CSS_URL = "https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.5.1/github-markdown-dark.min.css"

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
    return css

def render_markdown(md_text, dark=False):
    if plugin_gfm:
        md = mistune.create_markdown(plugins=[plugin_gfm()])
    else:
        md = mistune.create_markdown()
    html = md(md_text)
    css = get_github_css(dark)
    # Optimized scroll restoration script using sessionStorage (throttled for low CPU)
    scroll_script = """
    <script>
    (function() {
        var key = "fast_md_viewer_scroll";
        var lastSave = 0;
        var throttle = 120; // ms
        function saveScroll() {
            var now = Date.now();
            if (now - lastSave > throttle) {
                try { sessionStorage.setItem(key, window.scrollY); } catch (e) {}
                lastSave = now;
            }
        }
        function restoreScroll() {
            try {
                var y = parseInt(sessionStorage.getItem(key) || "0", 10);
                if (!isNaN(y)) window.scrollTo(0, y);
            } catch (e) {}
        }
        var scrollTimeout;
        window.addEventListener("scroll", function() {
            if (scrollTimeout) clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(saveScroll, throttle);
        }, {passive:true});
        window.addEventListener("beforeunload", saveScroll);
        window.addEventListener("pagehide", saveScroll);
        window.addEventListener("visibilitychange", function() {
            if (document.visibilityState === "hidden") saveScroll();
        });
        document.addEventListener("DOMContentLoaded", function() {
            setTimeout(restoreScroll, 0);
        });
        // Fallback: try again after a short delay in case of late layout
        window.addEventListener("load", function() {
            setTimeout(restoreScroll, 50);
        });
    })();
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
{scroll_script}
</body>
</html>
"""

class MarkdownViewer(Gtk.Window):
    def __init__(self, md_path):
        Gtk.Window.__init__(self, title="Fast MD Viewer (GitHub Style)")
        self.set_default_size(900, 700)
        self.md_path = md_path
        self.dark_mode = False
        self.zoom = 1.0

        # Overlay for button/label
        self.overlay = Gtk.Overlay()
        self.add(self.overlay)

        self.webview = WebKit2.WebView()
        settings = self.webview.get_settings()
        settings.set_enable_javascript(True)
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
        # No need for load-changed or _pending_scroll_y for scroll restoration

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
        self.zoom_label.set_size_request(-1, 20)

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