import logging
import sys
sys.path.append(".")

from duckfeed.model import Entry, Feed
from .feed_library import FeedLibrary
from .entry_reader import EntryReader
from .entry_list import EntryList
from .controller import Controller

from PySide6.QtWidgets import QWidget, QStackedWidget, QDockWidget, QMainWindow, QApplication
from PySide6.QtGui import QPalette
from PySide6.QtCore import Qt
from __feature__ import snake_case, true_property


class Gui(QMainWindow):
    """
    The main GUI object that displays app state.

    The `Gui` will NOT mutate any `Controller` state. `Gui` components
    will use callbacks to indicate any state changes, and the `Controller` can
    return information on whether to redraw, and any other contextual information.
    """

    def __init__(self, controller: Controller, *args, **kwargs):
        """
        Build and initialize a new `Gui` with the given `FeedList`. This will show the 
        every valid `Feed` in the `FeedLibrary`. This will not load their entries.
        """
        super().__init__(*args, **kwargs)
        self._controller = controller

        # resize to slightly smaller than screen
        self.resize(QApplication.primary_screen.size / 1.2)
        self.window_title = "Duck Feed"

        self.entry_reader = EntryReader(self)

        self.entry_list = EntryList(self)

        self.stacked_widget = QStackedWidget(self)
        self.stacked_widget.add_widget(self.entry_list)
        self.stacked_widget.add_widget(self.entry_reader)
        self.stacked_widget.current_index = 0  # show entry list first

        palette = QPalette()
        palette.set_color(QPalette.Window, Qt.white)
        self.stacked_widget.auto_fill_background = True
        self.stacked_widget.palette = palette
        self.set_central_widget(self.stacked_widget)

        # library on side menu
        self.library = FeedLibrary(self, self._controller)
        library_dock = QDockWidget(self)
        library_dock.set_title_bar_widget(QWidget())
        library_dock.set_widget(self.library)
        self.add_dock_widget(Qt.DockWidgetArea(1), library_dock)
        self.show()

    def add_entry(self, entry: Entry):
        """
        Add the given `Entry` to the GUI's `EntryList`.
        The entry should be fully downloaded and parsed.
        """
        self.entry_list.add_entry(entry)
    
    def open_entry(self, entry: Entry):
        """Open the `EntryReader` and display the given `Entry`."""
        try:
            self.entry_reader.open_entry(entry)
            self.stacked_widget.current_index = 1
        except Exception as e:
            logging.error(f"Failed to open entry: {e}")
    
    def reload_feed(self, feed: Feed):
        """Reload the `Feed` state and all entries in the `Gui`."""
        try:
            self.entry_list.reload_feed(feed)
        except Exception as e:
            logging.error(f"Failed to reload feed: {e}")

    def back(self) -> None:
        self.stacked_widget.current_index = 0
