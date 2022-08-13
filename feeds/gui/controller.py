import logging
import sys
import os
from multiprocessing import Manager
from typing import Optional
from appdirs import user_data_dir

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

import gui
from feeds.model import FeedList, Feed, FeedParseError, EntryCache, Entry
from feeds import APP_NAME


class Controller(QApplication):
    """
    The main interface to this application's GUI.
    This acts as a bridge between the model and the frontend.
    """

    def __init__(self) -> None:
        super().__init__(sys.argv)

        data_dir = user_data_dir(APP_NAME, APP_NAME)
        self.data_path = os.path.join(data_dir, "feeds.json")

        self._entry_queue = Manager().Queue()
        self._cache = EntryCache()
        self._feed_list = FeedList()
        self._feed_list.load(self.data_path, self._entry_queue, self._cache)
        self._gui = gui.Gui(self)

    def run(self):
        """Run the GUI and enter the application loop. This is a blocking call."""

        # periodically update the entries in the feed list from the entry queue
        timer = QTimer(self)
        timer.interval = 20
        timer.timeout.connect(self.update_entries)
        timer.start()

        self.exec_()

        self._feed_list.save(self.data_path)
        self._cache.save()

    
    def update_entries(self):
        """Add any entries in the entry queue to the inner `FeedList`."""
        while self._entry_queue.qsize() != 0:
            entry: Entry = self._entry_queue.get(block=False)
            self._gui.add_entry(entry)
        
    
    def add_feed(self, url: str) -> Optional[Feed]:
        """
        Add a `Feed` to the inner `FeedList`.
        
        Returns the added `Feed` if the operation was successful, `None` otherwise.
        """
        try:
            feed = Feed(url, self._entry_queue, self._cache)
            self._feed_list.append(feed)
            return feed
        except FeedParseError as e:
            logging.error(f"Failed to add feed at {url}: {e}")
            return None
    
    def edit_feed(self, feed: Feed, display: str, enabled: bool) -> None:
        """Edit the given feed with the updated parameters."""
        feed.display = display
        if feed.enabled != enabled:
            feed.enabled = enabled
            self._gui.reload_feed(feed)
    
    def remove_feed(self, feed: Feed):
        """Remove the given `Feed` from the inner `FeedList`."""
        feed.enabled = False
        self._feed_list.remove(feed)
        self._gui.reload_feed(feed)

    @property
    def feed_list(self) -> FeedList:
        """Inner `FeedList`."""
        return self._feed_list
