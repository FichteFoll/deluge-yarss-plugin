#
# Copyright (C) 2012-2019 bendikro bro.devel+yarss2@gmail.com
#
# This file is part of YaRSS2 and is licensed under GNU General Public License 3.0, or later, with
# the additional special exception to link portions of this program with the OpenSSL library.
# See LICENSE for more details.
#

import html

# Kept free of `gi` imports so that the markup logic is testable without GTK.


def escape(text):
    return html.escape(text)


def highlight_match(text, span, color):
    """Highlight `span`, a byte range into the UTF-8 encoding of `text`.

    The regex matching runs on the encoded title, so the offsets are byte offsets.
    """
    start, end = span
    encoded = text.encode("utf-8")
    before, match, after = (
        escape(part.decode("utf-8", errors="replace")) for part in (encoded[:start], encoded[start:end], encoded[end:])
    )
    return f'{before}<span background="{color}"><b>{match}</b></span>{after}'
