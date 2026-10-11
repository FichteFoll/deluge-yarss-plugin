#
# Copyright (C) 2012-2019 bendikro bro.devel+yarss2@gmail.com
#
# This file is part of YaRSS2 and is licensed under GNU General Public License 3.0, or later, with
# the additional special exception to link portions of this program with the OpenSSL library.
# See LICENSE for more details.
#

import threading
from unittest import mock

from twisted.internet import task
from twisted.internet.defer import Deferred, DeferredList
from twisted.python import threadable
from twisted.trial import unittest

import deluge.component as component
from deluge.error import DelugeError

import deluge_yarss2.util.common
import deluge_yarss2.yarss_config
from deluge_yarss2.rssfeed_scheduler import RSSFeedRunQueue, RSSFeedScheduler
from deluge_yarss2.util import logging
from deluge_yarss2.yarss_config import YARSSConfigChangedEvent

from . import common as test_common
from .test_torrent_handling import TestComponent
from .utils.log_utils import plugin_tests_logger_name

log = logging.getLogger(plugin_tests_logger_name)


class RSSFeedSchedulerTestCase(unittest.TestCase):
    def setUp(self):  # NOQA
        self.rssfeeds = test_common.get_default_rssfeeds(5)
        self.rssfeeds["0"]["update_interval"] = 1
        self.rssfeeds["1"]["update_interval"] = 3
        self.rssfeeds["2"]["update_interval"] = 10
        self.rssfeeds["3"]["update_interval"] = 30
        self.rssfeeds["4"]["update_interval"] = 120

        self.config = test_common.get_test_config()
        self.config.set_config(
            {"rssfeeds": self.rssfeeds, "email_configurations": {"send_email_on_torrent_events": False}}
        )

        self.scheduler = RSSFeedScheduler(self.config, log)
        test_component = TestComponent()
        self.scheduler.torrent_handler.download_torrent_file = test_component.download_torrent_file
        self.scheduler.enable_timers()

    def tearDown(self):  # NOQA
        # Must stop loopingcalls or test fails
        self.scheduler.disable_timers()

    def test_enable_timers(self):
        # Now verify the timers
        for key in self.scheduler.rssfeed_timers.keys():
            # Is the timer running?
            self.assertTrue(self.scheduler.rssfeed_timers[key]["timer"].running)

            # Does the timer have the correct interval?
            interval = self.scheduler.rssfeed_timers[key]["timer"].interval
            self.assertEqual(self.rssfeeds[key]["update_interval"] * 60, interval)
            self.assertEqual(
                self.rssfeeds[key]["update_interval"], self.scheduler.rssfeed_timers[key]["update_interval"]
            )

    def test_disable_timers(self):
        self.scheduler.disable_timers()

        # Now verify that the timers have been stopped
        for key in self.scheduler.rssfeed_timers.keys():
            # Is the timer running?
            self.assertFalse(self.scheduler.rssfeed_timers[key]["timer"].running)

    def test_delete_timer(self):
        # Delete timer
        self.assertTrue(self.scheduler.delete_timer("0"))
        self.assertFalse(self.scheduler.delete_timer("-1"))

        self.assertEqual(len(self.scheduler.rssfeed_timers.keys()), 4)
        self.assertFalse("0" in self.scheduler.rssfeed_timers)

    def test_reschedule_timer(self):
        clock, run_times = self.run_feeds_on_clock()
        self.scheduler.set_timer("0", 1)
        clock.pump([1] * 30)

        # Change interval to 60 minutes, counted from the start of the timer
        self.assertTrue(self.scheduler.set_timer("0", 60))
        self.assertEqual(self.scheduler.rssfeed_timers["0"]["update_interval"], 60)
        clock.pump([1] * 3600)

        self.assertEqual(self.scheduler.rssfeed_timers["0"]["timer"].interval, 60 * 60)
        self.assertEqual(run_times, [3601])

    def test_schedule_timer(self):
        # Add new timer (with key "5") with interval 60 minutes
        self.assertTrue(self.scheduler.set_timer("5", 60))

        # Verify timer values
        interval = self.scheduler.rssfeed_timers["5"]["timer"].interval
        self.assertEqual(60 * 60, interval)
        self.assertEqual(self.scheduler.rssfeed_timers["5"]["update_interval"], 60)

        # Should now be 6 timers
        self.assertEqual(len(self.scheduler.rssfeed_timers.keys()), 6)

    def test_rssfeed_update_handler(self):
        subscription = deluge_yarss2.yarss_config.get_fresh_subscription_config(rssfeed_key="0", key="0")
        self.config.set_config({"subscriptions": {"0": subscription}})

        # Check that last_update changes
        old_last_update = self.rssfeeds["0"]["last_update"]

        # Run the rssfeed with key 0
        self.scheduler.rssfeed_update_handler("0")
        self.assertNotEqual(old_last_update, self.rssfeeds["0"]["last_update"])

        old_last_update = self.rssfeeds["0"]["last_update"]

        # Run the subscription with key 0 like when the user runs it manually
        self.scheduler.rssfeed_update_handler(None, "0")

        # last_update should not have changed
        self.assertEqual(old_last_update, self.rssfeeds["0"]["last_update"])

    def test_rssfeed_update_handler_exception(self):
        subscription = deluge_yarss2.yarss_config.get_fresh_subscription_config(rssfeed_key="0", key="0")
        self.config.set_config({"subscriptions": {"0": subscription}})

        self.scheduler.rssfeed_update_handler_safe("0")
        # Run the rssfeed with invalid key
        self.assertRaises(KeyError, self.scheduler.rssfeed_update_handler, 1)
        # Safe function should not raise exception
        self.assertFalse(self.scheduler.rssfeed_update_handler_safe(1))

    def test_rssfeed_update_handler_safe_delugeerror(self):
        error = DelugeError("Failed to fetch RSS Feed")
        with mock.patch.object(self.scheduler.rssfeedhandler, "fetch_feed_torrents", side_effect=error):
            with mock.patch("traceback.print_exc") as print_exc:
                self.assertIsNone(self.scheduler.rssfeed_update_handler_safe("0"))
        print_exc.assert_not_called()

    def test_ttl_value_updated(self):
        config = test_common.get_test_config_dict()
        config["rssfeeds"]["0"]["update_interval"] = 30
        config["rssfeeds"]["0"]["obey_ttl"] = True
        config["rssfeeds"]["0"]["url"] = deluge_yarss2.util.common.get_resource(
            test_common.testdata_rssfeed_filename, path="tests"
        )

        yarss_config = test_common.get_test_config()
        yarss_config.set_config(config)

        self.scheduler.disable_timers()
        self.scheduler.yarss_config = yarss_config
        self.scheduler.enable_timers()

        def add_torrents_pass(*arg):
            pass

        self.scheduler.add_torrents_func = add_torrents_pass

        # The reactor registers its thread only once it runs, which trial does not do
        self.addCleanup(setattr, threadable, "ioThread", threadable.ioThread)
        threadable.registerAsIOThread()

        set_timer_in_io_thread = []
        set_timer = self.scheduler.set_timer

        def set_timer_recording_thread(*args, **kwargs):
            set_timer_in_io_thread.append(threadable.isInIOThread())
            return set_timer(*args, **kwargs)

        self.scheduler.set_timer = set_timer_recording_thread

        def verify_ttl_applied(result):
            self.assertEqual(set_timer_in_io_thread, [True])
            # Verify that update_interval of rssfeed in config was updated
            self.assertEqual(yarss_config.get_config()["rssfeeds"]["0"]["update_interval"], 60)
            # Verify that update_interval of the timer was updated
            self.assertEqual(self.scheduler.rssfeed_timers["0"]["update_interval"], 60)

        # Run the rssfeed with key 0
        d = self.scheduler.queue_rssfeed_update("0")
        return d.addCallback(verify_ttl_applied)

    def run_feeds_on_clock(self, ttl_on_first_run=None):
        """Runs feeds on a clock with a stub handler and returns the clock and the times of the runs."""
        self.scheduler.disable_timers()
        clock = task.Clock()
        self.scheduler.clock = clock
        self.scheduler.run_queue = ClockRunQueue(clock)
        self.scheduler.add_torrents_func = lambda *args: None
        run_times = []

        def run_feed(rssfeed_key=None, subscription_key=None):
            ttl_update = (rssfeed_key, ttl_on_first_run) if ttl_on_first_run and not run_times else None
            run_times.append(clock.seconds())
            return (self.scheduler.add_torrents_func, None, [], self.config.get_config(), ttl_update)

        self.scheduler.rssfeed_update_handler_safe = run_feed
        return clock, run_times

    def assert_one_timer_left_until_disabled(self, clock):
        self.assertEqual(len(clock.getDelayedCalls()), 1)
        self.scheduler.disable_timers()
        self.assertEqual(clock.getDelayedCalls(), [])

    def test_ttl_update_from_own_run_keeps_one_timer(self):
        clock, run_times = self.run_feeds_on_clock(ttl_on_first_run=2)
        self.rssfeeds["0"]["update_on_startup"] = True

        self.scheduler.set_timer("0", 1, update_on_startup=True)
        clock.pump([1] * 400)

        self.assertEqual(run_times, [1, 121, 241, 361])
        self.assert_one_timer_left_until_disabled(clock)

    def test_set_timer_during_own_run_keeps_one_timer(self):
        clock, run_times = self.run_feeds_on_clock()
        self.scheduler.set_timer("0", 1)
        clock.pump([1] * 60)

        # Like saving the feed while its scheduled run is still fetching
        self.scheduler.set_timer("0", 2)
        clock.pump([1] * 340)

        self.assertEqual(run_times, [61, 181, 301])
        self.assert_one_timer_left_until_disabled(clock)

    def test_set_timer_counts_new_interval_from_last_update(self):
        clock, run_times = self.run_feeds_on_clock()
        self.scheduler.set_timer("0", 2)
        clock.pump([1] * 150)

        # Updated at 120, so the next update is due at 300
        self.scheduler.set_timer("0", 3)
        clock.pump([1] * 250)

        # Updated at 300, so the next update would have been due at 360 and starts now
        self.scheduler.set_timer("0", 1)
        clock.advance(0)
        clock.pump([1] * 70)

        self.assertEqual(run_times, [121, 301, 401, 461])
        self.assert_one_timer_left_until_disabled(clock)

    def test_set_timer_counts_new_interval_from_manual_feed_update(self):
        clock, run_times = self.run_feeds_on_clock()
        self.scheduler.set_timer("0", 2)
        clock.pump([1] * 30)
        self.scheduler.queue_rssfeed_update("0")
        self.scheduler.queue_rssfeed_update(subscription_key="0")
        clock.pump([1] * 30)

        self.scheduler.set_timer("0", 3)
        clock.pump([1] * 180)

        self.assertEqual(run_times, [31, 31, 211])
        self.assert_one_timer_left_until_disabled(clock)

    def test_ttl_update_for_feed_deleted_during_its_run(self):
        clock, run_times = self.run_feeds_on_clock(ttl_on_first_run=2)
        added_torrents = []
        self.scheduler.add_torrents_func = lambda *args: added_torrents.append(args)
        self.scheduler.set_timer("0", 1)
        clock.pump([1] * 60)

        # Like deleting the feed while its scheduled run is still fetching
        del self.config.get_config()["rssfeeds"]["0"]
        self.scheduler.delete_timer("0")
        with self.assertNoLogs(plugin_tests_logger_name, level="WARNING"):
            clock.pump([1] * 60)

        self.assertEqual(run_times, [61])
        self.assertEqual(len(added_torrents), 1)
        self.assertEqual(clock.getDelayedCalls(), [])

    def test_rssfeed_update_queue(self):
        """Tests that the add_torrents_func is called the correct number of times,
        and that add_torrents_func is running in the main thread.
        """
        # Don't use the loopingcall, so disable just to avoid any trouble
        self.scheduler.disable_timers()
        self.config.set_config(test_common.get_test_config_dict())

        add_torrents_count = []
        main_thread = threading.current_thread()

        def add_torrents_cb(*arg):
            self.assertEqual(
                main_thread, threading.current_thread(), "add_torrents must be called from the main thread!"
            )
            add_torrents_count.append(0)

        self.scheduler.add_torrents_func = add_torrents_cb

        d_first = self.scheduler.queue_rssfeed_update(rssfeed_key="0")
        self.scheduler.queue_rssfeed_update(subscription_key="1")
        self.scheduler.queue_rssfeed_update(rssfeed_key="1")
        d_last = self.scheduler.queue_rssfeed_update(rssfeed_key="2")

        def verify_callback_count(args):
            self.assertEqual(len(add_torrents_count), 3)

        return DeferredList([d_first, d_last]).addBoth(verify_callback_count)

    def test_rssfeed_update_succeeds_when_adding_torrents_fails(self):
        """A failed Deferred would stop the LoopingCall of the feed for good."""
        self.scheduler.disable_timers()
        self.config.set_config(test_common.get_test_config_dict())

        def add_torrents_raise(*arg):
            raise RuntimeError("Failed to add torrents")

        self.scheduler.add_torrents_func = add_torrents_raise

        d = self.scheduler.queue_rssfeed_update(rssfeed_key="0")
        return d.addCallback(self.assertIsNone)

    def test_config_changed_event_emitted_on_io_thread(self):
        self.scheduler.disable_timers()
        self.config.set_config(test_common.get_test_config_dict())

        # The reactor registers its thread only once it runs, which trial does not do
        self.addCleanup(setattr, threadable, "ioThread", threadable.ioThread)
        threadable.registerAsIOThread()

        config_changed_in_io_thread = []

        def record_config_changed_event(event):
            if isinstance(event, YARSSConfigChangedEvent):
                config_changed_in_io_thread.append(threadable.isInIOThread())

        event_manager = mock.Mock()
        event_manager.emit.side_effect = record_config_changed_event
        patcher = mock.patch.object(component, "get", return_value=event_manager)
        patcher.start()
        self.addCleanup(patcher.stop)

        def add_torrents_pass(*arg):
            pass

        self.scheduler.add_torrents_func = add_torrents_pass

        def verify_emitted_on_io_thread(result):
            self.assertEqual(config_changed_in_io_thread, [True])

        d = self.scheduler.queue_rssfeed_update(rssfeed_key="0")
        return d.addCallback(verify_emitted_on_io_thread)


class ClockRunQueue:
    """Runs each job one second later on the clock instead of in a worker thread."""

    def __init__(self, clock):
        self.clock = clock

    def push(self, f, *args, **kwargs):
        return task.deferLater(self.clock, 1, f, *args, **kwargs)


class RSSFeedRunQueueTestCase(unittest.TestCase):
    def test_task_queue(self):
        """Test the RSSFeedRunQueue
        Test that the jobs are not run in main thread and that the jobs are run sequentially
        """
        main_thread = threading.current_thread()
        runtime_dict = {}

        def test_run(id):
            # Save the start and end time of the job
            runtime_dict[id] = {"start": deluge_yarss2.util.common.get_current_date()}
            # Test that the job is not run in main thread
            self.assertNotEqual(threading.current_thread(), main_thread)
            runtime_dict[id]["end"] = deluge_yarss2.util.common.get_current_date()
            return id

        result_callback_ids = []

        def result_callback(id):
            result_callback_ids.append(id)

        ids = [str(i) for i in range(10)]
        taskq = RSSFeedRunQueue()
        # Start id_count jobs
        for id in ids:
            d = taskq.push(test_run, str(id))
            d.addCallback(result_callback)

        def verify_times(arg):
            """Verify that start time is later than the previous job's end time"""
            tmp_date = deluge_yarss2.util.common.get_default_date()
            for id in range(len(ids)):
                runtime_dict[str(id)]
                self.assertTrue(tmp_date < runtime_dict[str(id)]["start"])
                tmp_date = runtime_dict[str(id)]["end"]

        d_verify = Deferred()
        d_verify.addCallback(verify_times)
        # Add verify_times to the last added deferred
        d.chainDeferred(d_verify)

        def verify_callback_results(args):
            self.assertEqual(len(ids), len(result_callback_ids))
            for i in range(len(ids)):
                self.assertEqual(ids[i], result_callback_ids[i])

        d_verify_callback = Deferred()
        d_verify_callback.addCallback(verify_callback_results)
        # Add verify_callback_results to the deferred chain
        d_verify.chainDeferred(d_verify_callback)
        return d_verify
