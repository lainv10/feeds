from duckfeed.model import Entry

from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QPushButton
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import Qt

from __feature__ import snake_case, true_property


ARTICLE_CSS = """
    <style>
    body {
        font-family: Helvetica, sans-serif;
        padding-left: 10em;
        padding-right: 10em;
    }

    .article-title {
        font-weight: bold;
        text-align: center;
    }

    img {
        margin: 1em;
        width: 100%;
        height: auto;
    }

    a {
        text-decoration: none;
        color: slateblue;
        transition: 0.3s;
    }

    a:hover {
        color: darkslateblue;
        border-bottom: 1px solid;
    }

    p {
        line-height: 2em;
    }

    ::selection {
        color: black;
        background: gold;
    }

    </style>
"""


class EntryReader(QWidget):
    """A reader for `Entry` HTML content."""

    BUTTON_QSS = """
        QPushButton { 
            background-color: #eee;
            padding: 0.25em;
            font-size: 16px;
            font-weight: bold;
            text-align: left;
            border-radius: 8px;
        }

        QPushButton:hover {
            background-color: #ddd
        }
    """
    

    def __init__(self, parent) -> None:
        """Create a new `EntryReader`."""
        super().__init__(parent)
        self.current_entry = None
        self._gui = parent
        self.build()

    def build(self) -> None:
        """Build this widget's UI."""

        open_browser_button = QPushButton("Open in Browser")
        open_browser_button.style_sheet = self.BUTTON_QSS
        open_browser_button.cursor = Qt.PointingHandCursor
        open_browser_button.clicked.connect(lambda: self.open_external(self.current_entry.link))

        back_button = QPushButton("Back")
        back_button.style_sheet = self.BUTTON_QSS
        back_button.cursor = Qt.PointingHandCursor
        back_button.clicked.connect(self.back)

        options_layout = QHBoxLayout()
        options_layout.add_widget(back_button)
        options_layout.add_stretch(1)
        options_layout.add_widget(open_browser_button)

        self.web_view = QWebEngineView()

        layout = QVBoxLayout(self)
        layout.add_layout(options_layout)
        layout.add_widget(self.web_view)

    def open_entry(self, entry: Entry):
        """Show the given `Entry` in this `EntryReader`."""
        self.web_view.set_page(RedirectingPage(self, parent=self.web_view))
        self.current_entry = entry
        top_image_html = f"<img src=\"{entry.top_image_url}\">"
        title_html = f"<h1 class=\"article-title\">{entry.title}</h1>"
        self.web_view.set_html(ARTICLE_CSS + top_image_html + title_html + entry.html)
    
    def open_external(self, url):
        """Open the given url in the system's default browser."""
        QDesktopServices.open_url(url)
    
    def back(self):
        self.web_view.page().delete_later()
        self._gui.back()


class RedirectingPage(QWebEnginePage):
    """A web engine page that redirects all clicked links to the system's browser."""
    def __init__(self, reader: EntryReader, *args, **kwargs):
        self._reader = reader
        super().__init__(*args, **kwargs)
    
    def accept_navigation_request(self, url, nav_type: QWebEnginePage.NavigationType, _) -> bool:
        """Redirect opening a URL to the system's browser."""
        if nav_type == QWebEnginePage.NavigationType.NavigationTypeLinkClicked:
            self._reader.open_external(url)
            return False
        return True
