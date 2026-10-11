#
# Copyright (C) 2012-2015 bendikro bro.devel+yarss2@gmail.com
#
# This file is part of YaRSS2 and is licensed under GNU General Public License 3.0, or later, with
# the additional special exception to link portions of this program with the OpenSSL library.
# See LICENSE for more details.
#

import functools
import traceback

import twisted.internet.defer as defer
from twisted.internet import reactor, threads
from twisted.internet.task import LoopingCall

import deluge.component as component
from deluge.error import DelugeError

from deluge_yarss2.rssfeed_handling import RSSFeedHandler
from deluge_yarss2.torrent_handling import TorrentHandler
from deluge_yarss2.yarss_config import YARSSConfigChangedEvent


class RSSFeedScheduler:
    """Handles scheduling the RSS Feed fetches."""

    def __init__(self, config, logger):
        self.yarss_config = config
        self.rssfeed_timers = {}
        self.run_queue = RSSFeedRunQueue()
        self.log = logger
        self.clock = reactor
        self.rssfeedhandler = RSSFeedHandler(logger)
        self.torrent_handler = TorrentHandler(logger)
        # To make it possible to disable adding torrents in testing
        self.add_torrents_func = self.torrent_handler.add_torrents

    def enable_timers(self):
        """Creates the LoopingCall timers, one for each RSS Feed"""
        config = self.yarss_config.get_config()
        for key in config["rssfeeds"]:
            rssfeed = config["rssfeeds"][key]
            self.set_timer(rssfeed["key"], rssfeed["update_interval"], rssfeed["update_on_startup"])
            self.log.info(f"Scheduled RSS Feed '{rssfeed['name']}' with interval {rssfeed['update_interval']}")

    def disable_timers(self):
        for key in list(self.rssfeed_timers.keys()):
            stop_timer(self.rssfeed_timers.pop(key))

    def set_timer(self, key, interval, update_on_startup=False):
        """Schedule a timer for the specified interval."""
        try:
            interval = int(interval)
        except ValueError:
            self.log.error(f"Failed to convert interval '{str(interval)}' to int!")
            return False
        interval_seconds = interval * 60
        now = self.clock.seconds()
        old_timer = self.rssfeed_timers.get(key)
        # A fresh LoopingCall, because a stopped one whose run is still in progress
        # would schedule its next call when that run finishes if it was restarted
        timer = LoopingCall(self.queue_rssfeed_update, key)
        timer.clock = self.clock
        if old_timer is None:
            # Start of the last update of the feed, or of the timer before the first update
            last_update = now
            delayed_start = None
            timer.start(interval_seconds, now=update_on_startup)
        else:
            stop_timer(old_timer)
            # Keep the time of the last update, so that a new interval counts from it
            last_update = old_timer["last_update"]
            delay = max(0, last_update + interval_seconds - now)
            delayed_start = self.clock.callLater(delay, timer.start, interval_seconds)
        self.rssfeed_timers[key] = {
            "timer": timer,
            "update_interval": interval,
            "last_update": last_update,
            "delayed_start": delayed_start,
        }
        return True

    def delete_timer(self, key):
        """Delete timer with the specified key."""
        if key not in self.rssfeed_timers:
            self.log.warning(f"Cannot delete timer. No timer with key {key}")
            return False
        stop_timer(self.rssfeed_timers.pop(key))
        return True

    def rssfeed_update_handler_safe(self, rssfeed_key=None, subscription_key=None):
        """
        This function is called by the LoopingCall, and should avoid passing any
        raised exceptions back to the loopingcall. This is to make sure the loopingcall
        doesn't stop.
        """
        try:
            return self.rssfeed_update_handler(rssfeed_key=rssfeed_key, subscription_key=subscription_key)
        except DelugeError:
            # Expected failures such as unreachable feeds, already logged where they are raised
            return None
        except:  # noqa: E722 do not use bare 'except'
            traceback.print_exc()
            exc_str = traceback.format_exc()
            self.log.warning(f"An exception was thrown by the RSS update handler. Please report this bug!\n{exc_str}")

    def rssfeed_update_handler(self, rssfeed_key=None, subscription_key=None):
        """Goes through all the feeds and runs the active ones.
        Multiple subscriptions on one RSS Feed will download the RSS feed page only once
        """
        if subscription_key:
            subscription_name = self.yarss_config.get_config()["subscriptions"][subscription_key]["name"]
            self.log.info(f"Manually running Subscription '{subscription_name}'")
        elif rssfeed_key:
            if self.yarss_config.get_config()["rssfeeds"][rssfeed_key]["active"] is False:
                return

        fetch_result = self.rssfeedhandler.fetch_feed_torrents(
            self.yarss_config.get_config(), rssfeed_key, subscription_key=subscription_key
        )
        matching_torrents = fetch_result["matching_torrents"]
        # Fetching the torrent files. Do this slow task in non-main thread.
        for torrent in matching_torrents:
            torrent["torrent_download"] = self.torrent_handler.get_torrent(torrent)

        ttl_update = None
        if "ttl" in fetch_result:
            # Subscription is run directly. Get RSS Feed key
            if not rssfeed_key:
                rssfeed_key = self.yarss_config.get_config()["subscriptions"][subscription_key]["rssfeed_key"]
            ttl_update = (rssfeed_key, fetch_result["ttl"])

        def save_subscription_func(subscription_data):
            self.yarss_config.generic_save_config("subscriptions", data_dict=subscription_data)

        return (
            self.add_torrents_func,
            save_subscription_func,
            fetch_result["matching_torrents"],
            self.yarss_config.get_config(),
            ttl_update,
        )

    def apply_ttl_update(self, rssfeed_key, ttl):
        # The feed may have been deleted or the timers disabled while it was running
        rssfeed = self.yarss_config.get_config()["rssfeeds"].get(rssfeed_key)
        if rssfeed is None:
            return
        self.log.info(f"Rescheduling RSS Feed '{rssfeed['name']}' with interval '{ttl}' according to TTL.")
        rssfeed["update_interval"] = ttl
        if rssfeed_key not in self.rssfeed_timers:
            return
        self.set_timer(rssfeed_key, ttl)

    def emit_config_changed_event(self):
        try:
            # Tests throws KeyError for EventManager when running this method, so wrap this in try/except
            component.get("EventManager").emit(YARSSConfigChangedEvent(self.yarss_config.get_config()))
        except KeyError:
            pass

    def add_torrents_callback(self, args):
        """
        Called on the reactor thread with the results from rssfeed_update_handler,
        which runs in a worker thread and must not use the timers, events or torrent manager.
        """
        if args is None:
            return
        add_torrents_func, save_subscription_func, matching_torrents, config, ttl_update = args
        try:
            if ttl_update:
                self.apply_ttl_update(*ttl_update)
            # Sends the updated config, e.g. last_update, to the GUI, even when there is nothing to add
            self.emit_config_changed_event()
            add_torrents_func(save_subscription_func, matching_torrents, config)
        except Exception:
            # A failure here would fail the Deferred and stop the LoopingCall of the feed for good
            exc_str = traceback.format_exc()
            self.log.warning(f"An exception was thrown when adding torrents. Please report this bug!\n{exc_str}")

    def queue_rssfeed_update(self, rssfeed_key=None, subscription_key=None):
        config = self.yarss_config.get_config()
        # Like last_update in the feed config, only updates of the whole feed count
        if subscription_key is None and rssfeed_key in self.rssfeed_timers:
            self.rssfeed_timers[rssfeed_key]["last_update"] = self.clock.seconds()
        queue_key = rssfeed_key
        if subscription_key is not None:
            queue_key = config["subscriptions"][subscription_key]["rssfeed_key"]
        self.run_queue.concurrent_max = get_max_concurrent_feeds(config.get("general", {}))
        job = functools.partial(
            self.rssfeed_update_handler_safe, rssfeed_key=rssfeed_key, subscription_key=subscription_key
        )
        return self.run_queue.push(queue_key, job, after=self.add_torrents_callback)


def get_max_concurrent_feeds(general_config):
    """Returns the configured number of parallel feed jobs, where any invalid value counts as 1."""
    value = general_config.get("max_concurrent_feeds", 1)
    # bool is a subclass of int, but not a number of feeds
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return 1
    return value


def stop_timer(timer):
    if timer["delayed_start"] and timer["delayed_start"].active():
        timer["delayed_start"].cancel()
    if timer["timer"].running:
        timer["timer"].stop()


class RSSFeedRunQueue:
    """Runs jobs in worker threads, at most concurrent_max at a time and at most one per key.

    A job's key stays taken until its `after` callable has returned on the reactor,
    so the next job of the same key starts only after the previous one is fully processed.
    Jobs that cannot start yet wait in FIFO order,
    and a waiting job does not hold up the jobs of other keys.
    """

    def __init__(self, concurrent_max=1):
        self.concurrent_max = concurrent_max
        self._running_keys = set()
        self._queued = []

    def push(self, key, job, after=None):
        """Queues the zero-argument callable job and returns a Deferred with its result.

        If given, after is called on the reactor with the job's result,
        and its return value becomes the result of the Deferred.
        """
        d = defer.Deferred()
        self._queued.append((key, job, after, d))
        self._start_queued()
        return d

    def _start_queued(self):
        # A loop, because concurrent_max may have been raised since the last start
        while len(self._running_keys) < self.concurrent_max:
            entry = next((entry for entry in self._queued if entry[0] not in self._running_keys), None)
            if entry is None:
                return
            self._queued.remove(entry)
            self._run(*entry)

    def _run(self, key, job, after, d):
        self._running_keys.add(key)
        job_d = threads.deferToThread(job)
        if after is not None:
            job_d.addCallback(after)
        job_d.addBoth(self._release, key)
        job_d.chainDeferred(d)

    def _release(self, result, key):
        self._running_keys.discard(key)
        self._start_queued()
        return result
