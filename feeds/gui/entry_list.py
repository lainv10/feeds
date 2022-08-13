import random
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QLabel, QFrame, QWidget, QScrollArea
from PySide6.QtGui import QCursor, QMouseEvent, QPixmap
from PySide6.QtCore import Qt, QMargins
from __feature__ import snake_case, true_property

from feeds.model import Entry, Feed


class EntryList(QScrollArea):
    """A widget for showing every `Entry` in each enabled `Feed`."""

    COLUMN_COUNT = 3

    def __init__(self, parent) -> None:
        """Create a new empty `EntryList`."""
        super().__init__(parent)
        self.columns: list[QVBoxLayout] = []
        self.items: dict[str, list[EntryListItem]] = {}
        self._gui = parent
        self.entry_count = 0
        self.build()

    def build(self) -> None:
        """Build this widget's UI."""
        list_widget = QWidget()
        self._layout = QHBoxLayout(list_widget)

        for _ in range(0, EntryList.COLUMN_COUNT):
            inner_layout = QVBoxLayout()
            inner_layout.set_spacing(10)
            outer_layout = QVBoxLayout()
            outer_layout.add_layout(inner_layout)
            outer_layout.add_stretch(1)
            self._layout.add_layout(outer_layout)
            self.columns.append(inner_layout)

        self.set_widget(list_widget)
        self.frame_shape = QFrame.NoFrame
        self.widget_resizable = True

    def add_entry(self, entry: Entry):
        """Add an `Entry` and display its information in this `EntryList`"""
        item = EntryListItem(self, entry)
        try:
            self.items[entry.parent_feed.url].append(item)
        except KeyError:
            self.items[entry.parent_feed.url] = [item]

        self.entry_count += 1

        column = self.columns[self.entry_count % EntryList.COLUMN_COUNT]
        if column.count() > 1:
            column.insert_widget(random.randint(0, column.count() - 1), item)
        else:
            column.add_widget(item)
        item.show() if entry.parent_feed.enabled else item.hide()
    
    def open_entry(self, entry: Entry):
        """Open this entry in the `Gui`."""
        self._gui.open_entry(entry)
    
    def reload_feed(self, feed: Feed):
        """Reload the entries of the given `Feed`."""
        items = self.items[feed.url]
        for item in items:
            item.show() if feed.enabled else item.hide()
    

class EntryListItem(QFrame):
    """A widget for showing a single `Entry` from a `Feed`."""

    QSS = """
        QFrame[objectName^="frame"] {
            padding: 0.5em; 
            border-radius: 0.5em;
        }

        QFrame[objectName^="frame"]:hover {
            background-color: #f0f0f0;
        }
    """

    def __init__(self, parent: EntryList, entry: Entry, *args, **kwargs):
        """Create a new empty `EntriesView`."""
        super().__init__(parent=parent, *args, **kwargs)
        self.entry = entry
        self.entry_list = parent

        self.build()

    def build(self) -> None:
        """Build this widget's UI."""

        self.entry_image_view = QLabel()
        self.entry_image_view.alignment = Qt.AlignCenter
        self.entry_image_view.style_sheet = "border-radius: 20px;"
        entry_image = self.entry.top_image
        if entry_image:
            self.pixmap = QPixmap()
            self.pixmap.load_from_data(entry_image)
            self.scale_pixmap()
        else:
            self.pixmap = None

        title_label = QLabel(self.entry.title)
        title_label.word_wrap = True
        title_label.style_sheet = "font-size: 16px; font-weight: bold;"

        # subtitle includes the date and an icon of the feed
        icon_label = QLabel()
        icon_image = self.entry.icon
        if icon_image:
            pixmap = QPixmap()
            pixmap.load_from_data(icon_image)
            icon_label.pixmap = pixmap.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        subtitle_label = QLabel(self.entry.date)
        subtitle_label.style_sheet = "font-size: 12px"
        subtitle_label.word_wrap = True

        subtitle_layout = QHBoxLayout()
        subtitle_layout.add_widget(icon_label)
        subtitle_layout.add_widget(subtitle_label)
        subtitle_layout.add_stretch(1)

        vertical_layout = QVBoxLayout(self)
        vertical_layout.contents_margins = QMargins(0, 0, 0, 0)
        vertical_layout.add_widget(self.entry_image_view)
        vertical_layout.add_widget(title_label)
        vertical_layout.add_layout(subtitle_layout)
        vertical_layout.add_stretch(1)

        self.object_name = "frame"
        self.style_sheet = EntryListItem.QSS
        self.cursor = QCursor(Qt.PointingHandCursor)
    
    def scale_pixmap(self):
        """Scale the pixmap of this item, if it exists, to the proper size."""
        scale_factor = EntryList.COLUMN_COUNT + 0.5
        if self.pixmap:
            self.entry_image_view.pixmap = self.pixmap.scaled(
                self.parent_widget().size / scale_factor, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def resize_event(self, event) -> None:
        """Resize the pixmap on resize event."""
        self.scale_pixmap()
        return super().resize_event(event)

    def mouse_press_event(self, event: QMouseEvent) -> None:
        """Open entry on mouse press event."""
        if (event.button() == 1):
            self.entry_list.open_entry(self.entry)
        return super().mouse_press_event(event)
