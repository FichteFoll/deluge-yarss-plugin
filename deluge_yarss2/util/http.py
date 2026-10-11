#
# Copyright (C) 2012-2015 bendikro bro.devel+yarss2@gmail.com
#
# This file is part of YaRSS2 and is licensed under GNU General Public License 3.0, or later, with
# the additional special exception to link portions of this program with the OpenSSL library.
# See LICENSE for more details.
#

import re
import ssl
import urllib.error
import urllib.parse as urlparse
import urllib.request
from html.parser import HTMLParser
from urllib.parse import quote as urllib_quote
from urllib.parse import quote_plus as urllib_quote_plus


def download_file(
    url_file_stream_or_string,
    site_cookies_dict=None,
    etag=None,
    modified=None,
    user_agent=None,
    referrer=None,
    handlers=None,
    request_headers=None,
    response_headers=None,
    resolve_relative_uris=None,
    sanitize_html=None,
    timeout="Global",
):
    from . import feedparsing

    result = dict(
        bozo=False,
        entries=[],
        feed={},
        headers={},
    )

    if site_cookies_dict:
        cookie_header = get_cookie_header(site_cookies_dict)
        if request_headers is None:
            request_headers = {}
        request_headers.update(cookie_header)

    data = feedparsing._open_resource(
        url_file_stream_or_string,
        etag,
        modified,
        user_agent,
        referrer,
        handlers,
        request_headers,
        result,
        timeout=timeout,
    )
    result["content"] = feedparsing.convert_to_utf8(result["headers"], data, result)
    return result


FETCH_URL_SCHEMES = ("http", "https")


def check_fetch_url_scheme(url):
    # urllib also opens file, ftp and data URLs, which must not be fetched from feed content.
    scheme = urlparse.urlsplit(url).scheme.lower()
    if scheme not in FETCH_URL_SCHEMES:
        raise ValueError(f"Unsupported URL scheme '{scheme}' in URL: '{url}'")


class HTTPOnlyRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        check_fetch_url_scheme(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_url(url, headers=None, timeout=None):
    """Returns the response body of a GET request to an http or https url.

    Raises `urllib.error.HTTPError` for HTTP error responses.
    Its `code` and `reason` describe the error, and its body can be read to show the error page to the user.
    `timeout` (seconds) applies to the connection and to each blocking read, `None` waits indefinitely.
    """
    check_fetch_url_scheme(url)
    # Preserves the previous `requests.get(..., verify=False)` behavior.
    # Enabling certificate verification is a separate decision.
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=context), HTTPOnlyRedirectHandler)
    request = urllib.request.Request(url, headers=headers or {})
    with opener.open(request, timeout=timeout) as response:
        return response.read()


def get_matching_cookies_dict(cookies, url):
    """Takes a dictionary of cookie key/values, and
    returns a dict with the cookies matching the url
    """
    matching_cookies = {}
    if not cookies:
        return {}
    for key in cookies.keys():
        if not cookies[key]["active"]:
            continue
        # Test url match
        if url.find(cookies[key]["site"]) != -1:
            for k2 in cookies[key]["value"].keys():
                matching_cookies[k2] = cookies[key]["value"][k2]
    return matching_cookies


def get_cookie_header(cookies, url=None):
    """Takes a dictionary of cookie key/values,
    and returns the cookies matching url encoded
    as required in the HTTP request header."""
    if url:
        cookies = get_matching_cookies_dict(cookies, url)
    if len(cookies) == 0:
        return {}
    return {"Cookie": encode_cookie_values(cookies)}


def encode_cookie_values(cookies_dict):
    """Takes a dictionary of key/value for a Cookie,
    and returns the cookie as used in a HTTP Header"""
    cookie_value = ""
    for key in sorted(cookies_dict):
        cookie_value += f"; {key}={cookies_dict[key]}"
    return cookie_value[2:]


def url_fix(s, charset="utf-8"):
    """Taken from werkzeug.utils. Liecense: BSD"""

    """Sometimes you get an URL by a user that just isn't a real
    URL because it contains unsafe characters like ' ' and so on.  This
    function can fix some of the problems in a similar way browsers
    handle data entered by the user:

    >>> url_fix(u'http://de.wikipedia.org/wiki/Elf (Begriffsklärung)')
    'http://de.wikipedia.org/wiki/Elf%20%28Begriffskl%C3%A4rung%29'

    :param charset: The target charset for the URL if the url was
                    given as unicode string.
    """
    scheme, netloc, path, qs, anchor = urlparse.urlsplit(s)
    path = urllib_quote(path, safe="%/:=&?~#+!$,;'@()*[]")
    qs = urllib_quote_plus(qs, ":&=")
    return urlparse.urlunsplit((scheme, netloc, path, qs, anchor))


def clean_html_body(html_page):
    if isinstance(html_page, bytes):
        html_page = html_page.decode("utf-8", errors="replace")

    stripper = HTMLStripper()
    stripper.feed(html_page)
    # Flush data HTMLParser held back because it could still be part of a longer token
    # (e.g. a trailing "&" that could start an entity reference).
    stripper.close()
    safe_html = stripper.get_data()

    # Allow max two consecutive \n
    safe_html = re.sub(r"\n(\n)+", r"\n\n", safe_html)
    return safe_html


class HTMLStripper(HTMLParser):
    # Tags that may appear in <head> without ending head mode.
    # HTML allows omitting </head>, so head mode also ends at <body> or at any
    # start tag that is not one of these, rather than only at a matching </head>.
    HEAD_ALLOWED_TAGS = {"title", "meta", "link", "base", "script", "style", "noscript", "template"}
    # Character data inside these elements is never shown to the user, in or out of <head>.
    SUPPRESSED_TAGS = {"script", "style"}

    def __init__(self):
        super().__init__()
        self.reset()
        self.fed = []
        self.in_head = False
        self.suppressed_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag == "head":
            self.in_head = True
        elif tag == "body":
            self.in_head = False
        elif self.in_head and tag not in self.HEAD_ALLOWED_TAGS:
            self.in_head = False

        if tag in self.SUPPRESSED_TAGS:
            self.suppressed_depth += 1

    def handle_endtag(self, tag):
        if tag == "head":
            self.in_head = False
        if tag in self.SUPPRESSED_TAGS and self.suppressed_depth > 0:
            self.suppressed_depth -= 1

    def handle_data(self, d):
        if not self.in_head and self.suppressed_depth == 0:
            self.fed.append(d)

    def get_data(self):
        prev_empty = False
        data = ""
        for i in self.fed:
            empty = i.strip() == ""
            if empty and prev_empty:
                continue
            elif empty:
                data += "\n"
            else:
                data += i.rstrip()
            prev_empty = empty
        return data
