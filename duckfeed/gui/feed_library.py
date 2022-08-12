from typing import Union
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QWidget, QPushButton, QVBoxLayout, QInputDialog, QFrame, QScrollArea, 
                                QDialog, QDialogButtonBox, QCheckBox, QFormLayout, QLineEdit, QMessageBox)
from PySide6.QtGui import QCursor, QPixmap, QIcon, QMouseEvent, QFont
from PySide6.QtCore import Qt, QMargins
from __feature__ import snake_case, true_property

from duckfeed.model import Feed, FeedList
from .controller import Controller


class FeedLibrary(QWidget):
    """
    A library view that shows a user their feeds, as well as allow them to manage feed
    sources, by adding or removing them.
    """

    BUTTON_QSS = """
        QPushButton { 
            background-color: #fff;
            padding: 0.25em;
            font-size: 20px;
            font-weight: bold;
            text-align: left;
            border-radius: 8px;
        }

        QPushButton:hover {
            background-color: #ddd
        }
    """

    def __init__(self, parent, controller: Controller) -> None:
        """Create a new `FeedLibrary` that shows a `FeedList`."""
        super().__init__(parent)
        self._controller = controller
        self.build()

    def build(self) -> None:
        """Build this widget's UI."""
        add_button = QPushButton("\uFF0B Add Feed")
        add_button.style_sheet = FeedLibrary.BUTTON_QSS
        add_button.cursor = QCursor(Qt.PointingHandCursor)
        add_button.clicked.connect(self._add_feed)

        scroll_area = QScrollArea(self)
        scroll_area.frame_shape = QFrame.NoFrame
        self.outer_layout = QVBoxLayout(scroll_area)
        self.scroll_layout = QVBoxLayout()
        self.scroll_layout.contents_margins = QMargins(0, 0, 0, 0)
        self.outer_layout.add_layout(self.scroll_layout)
        self.outer_layout.add_stretch(10)

        layout = QVBoxLayout(self)
        layout.add_widget(add_button)
        layout.add_widget(scroll_area)

        self.minimum_width = self.parent_widget().width / 5
        self._load_feed_list(self._controller.feed_list)

    def _load_feed_list(self, feed_list: FeedList):
        """Load the `FeedList` for this `FeedLibrary`."""
        for feed in feed_list.feeds:
            self._add_feed_item(feed)

    def _add_feed(self):
        """
        Open a dialog for the user to add a feed, and pass any 
        entered URL on to the `Controller`.
        """
        url, responded = QInputDialog.get_text(self, "Add Feed", "Feed URL:")
        if responded:
            feed = self._controller.add_feed(url)
            if feed:
                self._add_feed_item(feed)

    def _add_feed_item(self, feed: Feed):
        """Add a `FeedItem` to the library from the given `Feed`."""
        feed_item = FeedItem(self._controller, feed)
        self.scroll_layout.add_widget(feed_item)


class FeedItem(QFrame):
    """A view for showing an individual feed in one's library."""

    QSS = """
        QWidget#feed_item {
            background-color: #fff;
            padding: 0.4em;
            border-radius: 8px;
        }

        QWidget#feed_item:hover {
            background-color: #ddd;
        }
    """

    def __init__(self, controller: Controller, feed: Feed, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._controller = controller
        self._feed = feed
        self.build()

    def build(self):
        """Build this widget's UI."""
        self.object_name = "feed_item"
        self.cursor = Qt.PointingHandCursor
        self.style_sheet = self.QSS

        layout = QHBoxLayout(self)
        layout.contents_margins = QMargins(0, 0, 0, 0)
        layout.set_spacing(6)
        layout.set_alignment(Qt.AlignLeft)

        self.feed_name = QLabel(self._feed.display)
        font = QFont()
        font.set_point_size(12)
        self.feed_name.font = font

        self.icon_label = QLabel()
        icon_image = self._feed.icon
        if icon_image:
            self.pixmap = QPixmap()
            self.pixmap.load_from_data(icon_image)

            self.icon = QIcon()
            self.icon.add_pixmap(self.pixmap.scaled(
                32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation), QIcon.Active, QIcon.On)
            self.grayed_pixmap = self.icon.pixmap(
                self.pixmap.size(), QIcon.Disabled, QIcon.On)
            self.update()

        layout.add_widget(self.icon_label)
        layout.add_widget(self.feed_name)

    def mouse_press_event(self, event: QMouseEvent) -> None:
        """
        Open a dialog for editing the feed's properties. Any inputted information is
        passed to the `Controller`.

        If the feed is requested to be removed, this `FeedItem` will hide itself from the library.
        """
        if event.button() == 1:
            dialog = FeedEditDialog(self._feed)
            if dialog.exec_():
                (display, enabled, should_delete) = dialog.get_data()
                if should_delete:
                    self.hide()
                    self._controller.remove_feed(self._feed)
                else:
                    self._controller.edit_feed(self._feed, display, enabled)
                    self.update()
        return super().mouse_press_event(event)

    def update(self):
        """Update widget's view based on `Feed` state."""
        self.feed_name.text = self._feed.display
        pixmap = self.pixmap if self._feed.enabled else self.grayed_pixmap
        self.icon_label.pixmap = pixmap


class FeedEditDialog(QDialog):
    def __init__(self, feed: Feed, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._feed = feed
        self.should_remove = False
        self.build()

    def build(self):
        """Build this dialog's UI."""
        self.window_title = "Edit Feed"

        buttons = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        button_box = QDialogButtonBox(buttons)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        self.name_edit = QLineEdit()
        self.name_edit.text = self._feed.display

        self.enabled_checkbox = QCheckBox()
        self.enabled_checkbox.checked = self._feed.enabled

        delete_button = QPushButton("Remove Feed")
        delete_button.clicked.connect(self.open_removal_dialog)

        form = QFormLayout()
        form.add_row("Name", self.name_edit)
        form.add_row("Feed enabled", self.enabled_checkbox)
        form.add_row("", delete_button)

        layout = QVBoxLayout(self)
        layout.add_layout(form)
        layout.add_widget(button_box)

    def open_removal_dialog(self):
        """
        Open the feed removal deletion confirmation dialog.

        If the user confirms the feed removal, the `should_remove` flag is set to `True` for this dialog, 
        indicating to the caller that the user requested the associated feed should be removed.

        This finishes the dialog's execution.
        """
        confirm = QMessageBox()
        result = confirm.question(self, "Confirm feed removal",
                                  f"Are you sure you want to remove the feed '{self._feed.display}'?", confirm.Yes | confirm.No)
        if result == confirm.Yes:
            self.should_remove = True
            self.accept()

    def get_data(self) -> Union[str, bool, bool]:
        """
        Returns the current input data for this dialog, that the user may have edited.
        This includes the feed name, whether the feed should be enabled, and whether it
        should be deleted.

        Return tuple: (name_text: str, feed_enabled: bool, should_delete: bool)
        """
        return (self.name_edit.text, self.enabled_checkbox.checked, self.should_remove)
