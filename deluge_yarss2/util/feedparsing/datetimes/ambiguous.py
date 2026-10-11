from __future__ import absolute_import, unicode_literals

import datetime
import re

date_regex = re.compile(r"(?P<day>\d{2})/(?P<month>\d{2})/(?P<year>\d{4})\s(?P<hour>\d{2}):(?P<minutes>\d{2}):(?P<seconds>\d{2})")


def _parse_date_ambiguous(datestring):
    """ Handle dates formatted as 10/04/2014 03:44:14
    If the first value is actually the month, the result will be incorrect.
    """
    match = date_regex.match(datestring)
    if not match:
        return None
    d = match.groupdict()
    # Invalid values raise ValueError, which `_parse_date` handles.
    stamp = datetime.datetime(int(d["year"]), int(d["month"]), int(d["day"]),
                              int(d["hour"]), int(d["minutes"]), int(d["seconds"]))
    return stamp.utctimetuple()
