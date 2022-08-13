import logging
from pathlib import Path
import pickle
import feedparser
import urllib
import os
import threading
import json
import requests
import concurrent.futures

from multiprocessing import Queue
from newspaper import Article, Source
from typing import Optional
from appdirs import user_cache_dir

from .entry import Entry
from feeds import APP_NAME


class EntryCache:
    """A dictionary of cached entries. Each key is an `Entry` link."""

    def __init__(self) -> None:
        self.entries: dict[str, Entry] = {}
        # cache entries that were used from this instance
        self.used: dict[str, Entry] ={}
        cache_dir = user_cache_dir(APP_NAME, APP_NAME)
        self.cache_path = os.path.join(cache_dir, "entries.pickle")
        try:
            with open(self.cache_path, "rb") as cache_file:
                entries: dict[str, Entry] = pickle.load(cache_file)
                self.entries = entries
        except Exception as e:
            logging.error(f"Failed to load cache file: {e}")

    def save(self) -> None:
        """
        Save this `EntryCache` to a file on disk in the cache directory.
        Only the entries that were retrieved with `EntryCache.get` will be saved in
        the next cache.
        """
        try:
            Path(self.cache_path).parent.mkdir(exist_ok=True, parents=True)
            logging.info(f"saving cache to {self.cache_path}")
            with open(self.cache_path, "wb+") as cache_file:
                pickle.dump(self.used, cache_file)
        except Exception as e:
            logging.error(f"Failed to save cache to path: {e}")

    def get(self, link: str) -> Optional[Entry]:
        """
        Get the `Entry` assosciated to the given link.
        Will return `None` if the key does not exist.
        """
        try:
            entry = self.entries[link]
            self.used[link] = entry
            return entry
        except KeyError:
            return None

    def put(self, link: str, entry: Entry) -> None:
        """Insert a new link-entry pair into the cache."""
        self.entries[link] = entry


class FeedParseError(Exception):
    """Returned when an occurs during `Feed` parsing."""
    pass


class Feed:
    """An RSS/Atom feed."""

    def __init__(self, url: str, entry_queue: Queue, cache: EntryCache, display=None, enabled=True) -> None:
        """
        Create a new `Feed` given a feed's URL. This is a blocking network call.
        An entry queue should be passed. Each `Entry` that has finished downloading its
        content will be pushed onto this `Queue`.

        This will throw a `FeedParseError` if the feed at the given url cannot be parsed.
        """
        self._url = url
        self._enabled = enabled
        self._entries: list[Entry] = []

        try:
            self._feed: feedparser.FeedParserDict = feedparser.parse(url)
            first_link = self._feed.entries[0].link
            root_link = urllib.request.urlparse(first_link).hostname
            self._display = display if display else Source(first_link).brand.upper()
            # icon image using google's favicons API
            icon_url = f"https://www.google.com/s2/favicons?domain={root_link}&sz=32"
            self._icon = self._download_image(icon_url)
        except Exception as e:
            raise FeedParseError(f"Failed to parse feed from {url}: {e}")

        threading.Thread(target=self.download_entries, args=(
            entry_queue, cache), daemon=True).start()

    def download_entries(self, queue: Queue, cache: EntryCache):
        """Download every entry for this `Feed`."""

        def download_entry(entry_data: dict[str, str]):
            """
            Download a single feed entry from the information provided by an entry
            item in a `feedparser.FeedParserDict`.
            """
            cached = cache.get(entry_data.link)
            if cached:
                logging.info(f"using cached entry {cached.link}")
                cached._parent_feed = self
                feed_entry = cached
            else:
                article = Article(entry_data.link, keep_article_html=True)
                article.download()
                article.parse()

                # get images
                image = self._download_image(article.top_image)

                feed_entry = Entry(self, article, entry_data,
                              article.top_image, image, self._icon)
                cache.put(entry_data.link, feed_entry)
                cache.get(entry_data.link) # force into used list to save afterwards
                logging.info(f"cached entry {feed_entry.link}")
            self._entries.append(feed_entry)
            queue.put(feed_entry)

        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.map(download_entry, self._feed.entries)

    def _download_image(self, url) -> Optional[bytes]:
        """
        Return raw image data in bytes of the image at the given URL.
        This will return `None` if the image cannot be retrieved.
        """
        try:
            r = requests.get(url)
            if r.status_code == 200:
                return r.content
        except:
            return None

    @property
    def url(self) -> str:
        """The URL for this `Feed`."""
        return self._url

    @property
    def enabled(self) -> bool:
        """
        Information for frontends. Returns whether or not this
        feed is enabled and if its entries should be shown in the user's feed.

        This will be `True` when this `Feed` is first created.
        """
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        self._enabled = value

    @property
    def display(self) -> str:
        """Display name for this `Feed`."""
        return self._display

    @display.setter
    def display(self, value):
        self._display = value

    @property
    def entries(self) -> list[Entry]:
        """Get every `Entry` in this `Feed`."""
        return self._entries

    @property
    def icon(self) -> Optional[bytes]:
        """Image data in bytes of a small image representing this feed as an icon."""
        return self._icon


class FeedList:
    """Contains and manages every `Feed` added to a user's library."""

    def __init__(self) -> None:
        """Create a new empty `FeedList`."""
        self._feeds: list[Feed] = []

    def __getitem__(self, key):
        return self._feeds[key]

    @property
    def feeds(self) -> list[Feed]:
        """A list of every `Feed` in this `FeedList`."""
        return self._feeds

    @property
    def entries(self) -> list[Entry]:
        """Return every `Entry` from each enabled `Feed` in this `FeedList`"""
        entries = []
        for feed in self._feeds:
            if feed.enabled:
                entries.extend(feed.entries)
        return entries

    @property
    def len(self) -> int:
        """The number of feeds in this `FeedList`"""
        return len(self._feeds)

    def append(self, feed: Feed) -> None:
        """Append the given `Feed` to this `FeedList`."""
        self._feeds.append(feed)
    
    def remove(self, feed: Feed) -> None:
        """Remove the given `Feed` from this `FeedList`."""
        self._feeds.remove(feed)

    def save(self, path: str) -> None:
        """
        Write this `FeedList` as a JSON file at the given path.

        This will raise an `OSError` if the given file path cannot be opened.
        """
        try:
            Path(path).parent.mkdir(exist_ok=True, parents=True)
            with open(path, "w+") as json_file:
                feed_json = []
                for feed in self._feeds:
                    saved_state = {
                        "url": feed.url,
                        "display": feed.display,
                        "enabled": feed.enabled
                    }
                    feed_json.append(saved_state)
                json.dump(feed_json, json_file)
        except OSError as e:
            logging.error(f"Error while saving feed list to {path}: {e}")
            raise

    def load(self, path: str, queue: Queue, cache: EntryCache):
        """
        Load this `FeedList` with every `Feed` parsed from the given JSON file.

        Any feeds that cannot be parsed from the file will not be added to the list of feeds.

        The given `Queue` object will be passed to each created `Feed` object to allow
        access to entries that have finished downloading.
        """
        try:
            with open(path, "r+") as json_file:
                try:
                    feeds_data = json.load(json_file)
                    for data in feeds_data:
                        feed = Feed(data["url"].rstrip(), queue, cache, display=data["display"], enabled=data["enabled"])
                        self.append(feed)
                        logging.info(
                            f"Added feed from {feed.url}")
                except FeedParseError as e:
                    logging.error(f"Error while processing feed: {e}")

        except Exception as e:
            logging.error(f"Error loading data file {path}: {e}")
