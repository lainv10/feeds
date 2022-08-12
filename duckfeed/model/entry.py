from typing import Optional
import datetime

from newspaper import Article


class Entry:
    """An individual article entry in a `Feed`."""

    def __init__(self, parent, article: Article, entry: dict[str, str], top_image_url: str, top_image: bytes = None, icon_image: bytes = None) -> None:
        """
        Create a new `Entry` with a parent `Feed` and with data provided by a
        `newspaper.Article` as well as a `feedparser.FeedParserDict` entry.

        Top image url data for the article can be provided as a list of bytes.
        """
        self._parent_feed = parent
        self._title = entry.title
        self._link = entry.link
        self._html = article.article_html
        self._top_image = top_image
        self._top_image_url = top_image_url
        self._icon = icon_image

        try:
            date = entry.published_parsed
        except:
            try:
                date = entry.created_parsed
            except:
                self._date = ""
                return
        self._construct_date(datetime.datetime(*(date[:6])))

    def _construct_date(self, date: datetime.datetime):
        """Construct the date string for this entry from a `datetime` object"""
        delta: datetime.timedelta = datetime.datetime.now() - date
        months = delta.days // 30
        hours = delta.seconds // 3600
        minutes = delta.seconds // 60
        if months > 0:
            value = months
            unit = "month"
        elif delta.days > 0:
            value = delta.days
            unit = "day"
        elif hours > 0:
            value = hours
            unit = "hour"
        else:
            value = minutes
            unit = "minute"
        if value > 1:
            unit = unit + "s"

        self._date = f"{value} {unit} ago"

    @property
    def parent_feed(self):
        """The `Feed` this `Entry` belongs to."""
        return self._parent_feed

    @property
    def title(self) -> str:
        """The title for this `Entry."""
        return self._title

    @property
    def link(self) -> str:
        """The link to the full article for this `Entry`"""
        return self._link

    @property
    def html(self) -> Optional[str]:
        """Simplified HTML string of the article for this `Entry`."""
        return self._html

    @property
    def top_image(self) -> Optional[bytes]:
        """
        The image data in bytes of the top image for this entry's article.

        This will be `None` if this entry's article has not been downloaded and parsed yet.
        Alternatively, it may be `None` if the parsing failed, or if the entry has no top image.
        """
        return self._top_image

    @property
    def top_image_url(self) -> str:
        """The image URL for the entry article's top image."""
        return self._top_image_url

    @property
    def icon(self) -> Optional[bytes]:
        """A small image showing the icon of the `Feed` this `Entry` belongs to."""
        return self._icon

    @property
    def date(self) -> str:
        """A formatted string representing the relative date that this `Entry` was created/published."""
        return self._date
