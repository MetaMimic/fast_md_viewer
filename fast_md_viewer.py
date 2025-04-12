#!/usr/bin/env python3
import sys
import os

try:
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk, Gdk, Pango
except ImportError:
    print("Error: python3-gi (PyGObject) is not installed. Please install it with 'sudo apt install python3-gi'.")
    sys.exit(1)

try:
    import mistune
except ImportError:
    print("Error: mistune is not installed. Please install it with 'sudo apt install python3-mistune'.")
    sys.exit(1)

import webbrowser

BASE_FONT_SIZE = 14

from html.parser import HTMLParser

def md_to_pango(md_text, base_font_size):
    # Use mistune.Markdown() for compatibility
    html = mistune.markdown(md_text)
    # Convert HTML to Pango markup (very basic, handles most common tags)
    class HTMLToPango(HTMLParser):
        def __init__(self):
            super().__init__()
            self.result = []
            self.tag_stack = []
            self.font_size = base_font_size
        def handle_starttag(self, tag, attrs):
            if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
                size = self.font_size + 8 - 2 * int(tag[1])
                self.result.append(f"<b><span size='{size}pt'>")
                self.tag_stack.append(f"</span></b>")
            elif tag == "b" or tag == "strong":
                self.result.append("<b>")
                self.tag_stack.append("</b>")
            elif tag == "i" or tag == "em":
                self.result.append("<i>")
                self.tag_stack.append("</i>")
            elif tag == "tt" or tag == "code":
                self.result.append("<tt>")
                self.tag_stack.append("</tt>")
            elif tag == "ul":
                self.result.append("")
                self.tag_stack.append("")
            elif tag == "ol":
                self.result.append("")
                self.tag_stack.append("")
            elif tag == "li":
                self.result.append("• ")
                self.tag_stack.append("")
            elif tag == "blockquote":
                self.result.append('<span foreground="#888">│ </span>')
                self.tag_stack.append("")
            elif tag == "a":
                # Ignore <a> tags in Pango markup, just render the text
                self.tag_stack.append("")
            elif tag == "hr":
                self.result.append("────────────────────────────")
                self.tag_stack.append("")
            else:
                self.tag_stack.append("")
        def handle_endtag(self, tag):
            if self.tag_stack:
                self.result.append(self.tag_stack.pop())
        def handle_data(self, data):
            self.result.append(self.escape(data))
        def escape(self, s):
            return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        def get_markup(self):
            return "".join(self.result)
    parser = HTMLToPango()
    parser.feed(html)
    return parser.get_markup()

class MarkdownViewer(Gtk.Window):
    def __init__(self, md_path):
        Gtk.Window.__init__(self, title="Fast MD Viewer")
        self.set_default_size(800, 600)
        self.base_font_size = BASE_FONT_SIZE
        self.md_path = md_path

        self.scrolled = Gtk.ScrolledWindow()
        self.add(self.scrolled)

        self.textview = Gtk.TextView()
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD)
        self.textview.set_editable(False)
        self.textview.set_cursor_visible(False)
        self.textview.set_left_margin(16)
        self.textview.set_right_margin(16)
        # Use CSS for font size (modern GTK)
        css = Gtk.CssProvider()
        css.load_from_data(f"textview {{ font-family: Monospace; font-size: {self.base_font_size}pt; }}".encode())
        self.textview.get_style_context().add_provider(css, Gtk.STYLE_PROVIDER_PRIORITY_USER)
        self.scrolled.add(self.textview)

        self.buffer = self.textview.get_buffer()
        self.load_markdown()

        # Ctrl+scroll for zoom
        self.textview.connect("scroll-event", self.on_scroll)

        # Make links clickable
        self.textview.connect("event-after", self.on_event_after)

    def load_markdown(self):
        try:
            with open(self.md_path, "r", encoding="utf-8") as f:
                md_text = f.read()
        except Exception as e:
            self.buffer.set_text("Failed to load file: {}".format(e))
            return
        markup = md_to_pango(md_text, self.base_font_size)
        self.buffer.set_text("")
        self.buffer.insert_markup(self.buffer.get_start_iter(), markup, -1)
        # Tag links
        start = self.buffer.get_start_iter()
        while True:
            match = start.forward_search('<a href="', 0, None)
            if not match:
                break
            match_start, match_end = match
            href_start = match_end.copy()
            href_end = href_start.copy()
            href_end.forward_search('">', 0, None)
            href = self.buffer.get_text(href_start, href_end, False)
            tag = self.buffer.create_tag(None, foreground="#1565c0", underline=Pango.Underline.SINGLE)
            self.buffer.apply_tag(tag, match_start, href_end)
            start = href_end

    def on_scroll(self, widget, event):
        if event.state & Gdk.ModifierType.CONTROL_MASK:
            if event.direction == Gdk.ScrollDirection.UP:
                self.base_font_size = min(self.base_font_size + 1, 48)
            elif event.direction == Gdk.ScrollDirection.DOWN:
                self.base_font_size = max(self.base_font_size - 1, 6)
            # Update font size using CSS
            css = Gtk.CssProvider()
            css.load_from_data(f"textview {{ font-family: Monospace; font-size: {self.base_font_size}pt; }}".encode())
            self.textview.get_style_context().add_provider(css, Gtk.STYLE_PROVIDER_PRIORITY_USER)
            self.load_markdown()
            return True
        return False

    def on_event_after(self, widget, event):
        if event.type == Gdk.EventType.BUTTON_RELEASE and event.button == 1:
            x, y = event.x, event.y
            iter_ = self.textview.get_iter_at_location(int(x), int(y))
            tags = iter_.get_tags()
            for tag in tags:
                if tag.get_property("underline") == Pango.Underline.SINGLE:
                    # Extract href from buffer text
                    # (This is a simplification; a more robust approach would store href in tag data)
                    # For now, just open the first URL found in the line
                    line = self.buffer.get_text(self.buffer.get_iter_at_line(iter_.get_line()), self.buffer.get_iter_at_line(iter_.get_line()+1), False)
                    import re
                    m = re.search(r'<a href="([^"]+)"', line)
                    if m:
                        webbrowser.open(m.group(1))
                        return

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