# Changelog

References of the form `bendikro#<num>` refer to issues
in the [original repository on Bitbucket](https://bitbucket.org/bendikro/deluge-yarss-plugin).
Bitbucket has since discontinued its issue tracker,
so these issues are no longer available.

## Unreleased

This release moves the project to GitHub
and makes the plugin work with current versions of Python, setuptools and Deluge.
It also contains a large number of bug fixes,
most of which are listed in the collapsed section below.

### Upgrade Notes

* Raised the minimum supported Python version to 3.11
* Feed item dates with a UTC offset are now compared correctly; the first update after upgrading may once skip or re-add items published close to the last match
* "Set now" for a subscription's last matched timestamp no longer stores local time as UTC; set the last match again for subscriptions where it was set with "Set now"
* Torrent downloads now verify TLS certificates against the system's default CA store
* Added a per-feed option to skip TLS certificate verification, for trackers with self-signed certificates
* Cookies are now matched to sites by hostname instead of substring; partial site names such as `example` no longer match `tracker.example.org`

### Highlights

* Moved the project to GitHub
* Fixed loading the plugin without pkg_resources, which setuptools 82 removed and the importlib-based plugin loader does not support
* Fixed compatibility with Python 3.12 and 3.13
* Fixed the Web UI plugin entry point
* Added a "Maximum parallel feed fetches" setting (`max_concurrent_feeds`, default 1) that lets several feeds update at the same time; updates of the same feed never overlap
* Scheduled feed updates now send `If-None-Match` / `If-Modified-Since` and skip downloading and parsing feeds the server reports as unchanged; the validators are kept in memory only
* Fixed torrent downloads blocking the Deluge daemon without a timeout; they now time out after 30 seconds
* Fixed a feed's update timer stopping for good after an error while adding its matched torrents
* Fixed a refused magnet link aborting the remaining matched torrents
* Fixed labels not being applied to torrents added from magnet links
* Fixed email notifications sending the torrents of another notification when several notifications fired in the same run

<details>
<summary>All other changes</summary>

#### Feeds and Scheduling

* Fixed feed item dates with a UTC offset being compared as if they were UTC wall time; on the first update after upgrading the plugin, feeds with a non-zero offset may skip items published within the offset after the last match (positive offsets) or re-add up to the offset's hours worth of old items (negative offsets), a one-time effect that cannot be migrated
* Fixed "Set now" for a subscription's last matched timestamp storing local wall clock time labelled as UTC, which could skip or re-add items for users at a non-zero UTC offset; a feed's last update was also shown with the wrong offset
* Reduced the log output for unreachable RSS feeds from a stacktrace to a single warning
* Fixed a TTL warning being logged on every update of feeds without a TTL
* Fixed feeds with a non-integer TTL or image width, or a publish date with an out-of-range UTC offset, having all of their items dropped instead of just the malformed value
* Fixed unparsable feed responses, including broken RSS documents without a channel, raising an error instead of being reported as a bozo result
* Recognized B, KB, KiB, MiB, GiB, TB and TiB sizes in item descriptions, interpreted as binary and reported in KiB/MiB/GiB/TiB like the Deluge client
* The warning for unparsable dates now includes the parse error detail
* Fixed the log message for matching feed items without a publish date claiming an old timestamp, instead of explaining that the item has no publish date and that enabling "Ignore timestamp" would add it
* Fixed a feed being updated twice per interval after its TTL changed during a scheduled update, with each further TTL change adding another update per interval
* Changed a new update interval of a feed, whether saved in its settings or taken from its TTL, to count from the feed's last update instead of from the change, updating right away if that time has already passed
* Fixed a feed's next update possibly starting before the previous update had saved its last match, which could add the same item twice

#### Adding Torrents

* Fixed invalid torrent files still being passed to Deluge
* Fixed the sequential download option being applied only when auto-managed was also set
* Torrent download errors now name the HTTP status instead of a misleading "Unable to decode torrent file"
* Fixed a crash when a tracker's digest authentication challenge had no realm
* Fixed the add_torrent RPC downloading the torrent file on the reactor thread, which could stall the daemon when the server was slow
* Fixed thread-unsafe calls to reactor APIs for TTL rescheduling and event emission from feed and email worker threads

#### Email Notifications

* Fixed notification emails carrying over the content of an earlier notification when several fired in the same run, and feed-provided torrent titles and subscription names not being HTML-escaped in the HTML part; the user's own template text is used unescaped
* Fixed `$torrentlist` not being replaced in the HTML part of a notification email when it ended the message or was followed by other text on the same line
* Fixed sending an html-only notification email raising a KeyError
* Fixed SMTP connections being left open and never timing out; they now close on every path and time out after 30 seconds
* Fixed a crash when a subscription referenced a deleted email notification message; the notification is now skipped with a warning

#### User Interface

* Fixed feed titles and subscription names with `&` or `<` not rendering correctly in the subscription dialog, and regex match highlighting using the wrong offsets for titles with non-ASCII characters
* Fixed the subscription dialog not showing feed fetch errors, and its "show as text" view not showing the cleaned page text of an unparsable response
* Fixed a crash in the subscription dialog when the Label plugin is disabled, and a crash in the path chooser's completion list on pointer motion events
* Fixed crashes in the GTK UI when right-clicking the cookie list, copying a cookie to the clipboard, right-clicking below the rows of the matching list, or opening the dummy feed
* Fixed the feed dialog deriving the site name from an unstripped URL
* Fixed cancelling a dialog in the GTK UI still saving its edits to the cached configuration
* Fixed disabling the GTK UI plugin leaving its event handlers registered
* Fixed `fieldset` being an implicit global in the Web UI script `data/yarss2.js`

#### Packaging and Development

* Renamed the package from yarss2 to deluge_yarss2
* Replaced setup.py, tox, flake8 and isort with pyproject.toml, uv, ruff and GitHub Actions
* Replaced requests and BeautifulSoup with the Python standard library
* Refreshed the vendored third-party libraries
* Several fixes were ported from the TSA3000 and trasherdk forks

</details>

## v2.1.5 - 2021-03-21

* Fix bendikro#63: Fix error on python 3.9 due to bug in feedparser

## v2.1.4 - 2019-10-23

* Fix bendikro#53: Fix bug introduced in v2.1.2 where showing the RSS feed results was
  broken in thin client mode.
* Fix bendikro#48: Reduce the minimum updating interval from 5 to 1 minute.

## v2.1.3 - 2019-10-17

* Fix bendikro#43: Unable to add Cookie-information

## v2.1.2 - 2019-10-17

* Fix bendikro#53: Download RSS feeds via the plugin core (on the server)

## v2.1.1 - 2019-10-15

* Fix: Bug adding torrent links to deluge

## v2.1.0 - 2019-10-09

* Add WebUI Preferences page to inform that the plugin must be managed through the GTK UI client

## v2.0.0 - 2019-10-04

* Fix bendikro#54: Add support for Deluge 2.X
* Replaced [feedparser](https://github.com/kurtmckee/feedparser) with
  [atoma](https://github.com/NicolasLM/atoma) for parsing RSS feeds

Note: YaRSS2 v2.X does not support Deluge 1.3.X

## v1.4.3 - 2015-11-14

* Fix bendikro#10: Option to make YaRSS2 fetch subscriptions on startup
* Fix bendikro#13: Moved sending test email from daemon instead of client
* Fix bendikro#14: Problem with the ISO formating of 'Last matched' timestamp
* Fix bendikro#15: python traceback when RSS feed has no items
* Fix bendikro#20: An exception was thrown by the RSS update handler

## v1.4.2 - 2015-11-11

* Fixed bendikro#26: Labels don't stay after restart
* Fixed bendikro#27: "Add torrent" on right click menu in subscription dialog gives stacktrace

## v1.4.1 - 2015-10-06

* Fixed bendikro#24: Adding a second feed/subscription deleted previous

## v1.4.0 - 2015-09-29

* Implemented support for setting label when Label plugin is enabled
* Updated feedparser to 5.2.0
* Updated requests library to v2.7
* Change user agent used when fetching RSS feeds with requests library.
* Added option to ignore timestamps in RSS feeds.
* Added option to prefer magnet links over torrent links if both are available.

## v1.3.3 - 2014-07-25

* Updated feedparser to 5.1.3
* Fix Libtorrent error when adding magnet links in Deluge 1.3.3

## v1.3.2 - 2013-12-10

### Features

* Now handles RSS url's that have spaces
* Added right click option to copy a cookie

### Bug Fixes

* Fix log window causing crash of Deluge.

## v1.3.1 - 2013-10-06

* Fix incorrect handler in exclude regex textbox (Bart Nagel)
* Included missing file for Windows. (gtk.keysyms)

## v1.3.0 - 2013-09-27

* Added new path chooser to settings.
* If an error occurs when fetching RSS feeds it should no longer stop the
  scheduler from running.

## v1.2.1 - 2013-01-12

* Fixed bug causing running subscriptions manually to fail.

## v1.2.0 - 2012-12-10

### Features

* Added new options in the subscription dialog (Bandwidth, General).
* Added support for the enclosure tag in RSS feeds.
* Using the requests library to handle redirects properly so that non-direct
  torrent links work.
* Added "Copy link to clipboard" button to the right click menu in the
  subscription panel.
* When failing to download a torrent in the dialog subscription, the page
  content is now shown in a message pane at the bottom.
* Removed GTK (client) dependency on libtorrent-python

### Bug Fixes

* Fixed bug crashing Deluge when adding torrents
* The checkbox ("On torrent added") to enable a notification in the list of
  notifications
  for a subscription was not working.
* Tooltips were displayed on the wrong row.

## v1.1.3 - 2012-10-17

* Fixed bug that caused sending emails to fail.
* The 'From email address' field value in configurations was not loaded.
* Improved verification of the config on startup. (Fix errors)

## v1.1.2 - 2012-10-05

* Fixed error where ComboBox.get_active_text would return None.
* The current value in "Move completed" and "Download location" was added twice.

## v1.1.1 - 2012-10-03

* Fixed import error when running YaRSS2 on daemon without gtk installed.
* feedparser library was unable to parse some timestamps.
* The order of the torrents in the torrent list in the subscription dialog was incorrect.

## v1.1.0 - 2012-09-12

* Added panel for log messages.
* Added functionality to reset the last matched timestamp for subscriptions. (Options tab in subscription dialog)
* Fixed bug where RSS feeds with no proper tag for the timestamp when the torrent was published would crash YaRSS2.
* Fixed bug where the 'Published' column in matching panel for subscriptions wasn't properly populated.
* Hopefully fixed bug in GUI that could result in Deluge crashing.

## v1.0.4 - 2012-06-27

* Added support for magnet links.
* Running RSS feed fetches in separate thread to avoid having the deluge daemon being busy for too long.
* Added option "Obey TTL" in RSS Feed dialog. With this checked the "Update Interval" will be updated with the TTL value of the RSS Feed.
* Added option "Download location" in subscription dialog.
* Fixed bug where it was possible to delete an email message used by subscriptions for notifications.

## v1.0.3 - 2012-05-17

* When adding a RSS Feed or changing the RSS Feed update interval the RSS Feed is now properly (re)schedules with the (new) update interval.
  (Previously a restart of deluge was required)
* After deleting a RSS Feed it is properly stopped from running.
* Added timeout for 10 seconds on feedparser so deluge won't hang in case the server doesn't respond properly.
* "Last update" field in RSS Feeds is now updated properly.
* Added "Last matched" field in Subscriptions list with the timestamp for when the subscription last matched a torrent.
* No longer allow deleting RSS Feeds with subscriptions registered.
* Fixed issue in feedparser where '&' in torrent URLs was converted to &amp.

## v1.0.2 - 2012-04-07

* Added mime modules for sending email (required on Windows).

## v1.0.1 - 2012-04-01

* Unicode characers can now be used to search.
* Added tests to test some of the most important functionality

## v1.0 - 2012-03-27

* First release

(Tested with Deluge 1.3.5)
