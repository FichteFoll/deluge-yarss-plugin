# YaRSS2

Yet another RSS 2, an RSS plugin for Deluge.

Author: Bro <bro.development@gmail.com>

Based on YaRSS by Camillo Dell'mour.

## Compatibility

Deluge 2.2, both with the stock plugin loader and the importlib-based plugin loader.

Python 3.11 to 3.14.

## Installation

Download `YaRSS2-<version>-py3.egg` from the GitHub releases.
One egg works for all supported Python versions.

Install it via Preferences > Plugins > Install Plugin,
or copy it into `~/.config/deluge/plugins`.
Then enable it.

## Development

Set up the environment with:

```
uv sync
```

Run the test suite with:

```
uv run pytest
```

GUI tests need a display and GTK/GObject introspection dev packages.
Install them with `uv sync --group gui`,
then run them with:

```
uv run pytest -m gui
```

Lint and format the code with:

```
uv run ruff check
uv run ruff format
```

Build the egg with:

```
uv run scripts/build_egg.py
```

Link the source tree into a Deluge config directory for development with:

```
uv run scripts/dev_link.py [--config DIR]
```

Smoke-test an egg in a throwaway daemon with:

```
uv run scripts/smoke_test.py dist/YaRSS2-*.egg
```

To run a throwaway daemon for manual testing:

```
uv run deluged -c /tmp/deluge-dev -d -L debug
```

`deluge-console` and `deluge-web` accept the same `-c` option.

To update a vendored library,
edit `deluge_yarss2/_vendor/vendor.txt`,
then run:

```
uv run --only-group vendor vendoring sync
```

Then run `uv sync` to restore the development environment.

`deluge_yarss2/atoma` is a maintained fork of
[atoma](https://github.com/NicolasLM/atoma),
and `deluge_yarss2/util/feedparsing` is a fork of
[feedparser](https://github.com/kurtmckee/feedparser) HTTP and encoding code.
Both are kept as first-party code rather than vendored,
and are excluded from linting and formatting.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## Licensing

YaRSS2 itself is licensed under the GNU General Public License version 3 or later,
see [LICENSE](LICENSE).

It bundles third-party code under GPL-compatible licenses,
each with its license file next to the code:

- `deluge_yarss2/atoma` is a fork of
  [atoma](https://github.com/NicolasLM/atoma),
  licensed under the MIT license.
- `deluge_yarss2/util/feedparsing` is derived from
  [feedparser](https://github.com/kurtmckee/feedparser),
  licensed under the BSD 2-Clause license.
  The exception is `datetimes/ambiguous.py`,
  which was written for YaRSS2 and is licensed under the GPLv3.
- The libraries vendored into `deluge_yarss2/_vendor`
  carry their own license files there.
  These are python-dateutil (Apache 2.0 and BSD 3-Clause),
  six (MIT) and defusedxml (PSF 2.0).
