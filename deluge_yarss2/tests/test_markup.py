from twisted.trial import unittest

from deluge_yarss2.gtk3ui import markup


def byte_span(text, part):
    encoded = text.encode("utf-8")
    start = encoded.index(part.encode("utf-8"))
    return start, start + len(part.encode("utf-8"))


# Plain pytest functions run inside the reactor greenlet of pytest-twisted,
# which leaves the reactor unusable for the trial test cases collected after them.
class MarkupTestCase(unittest.TestCase):
    def test_escape(self):
        self.assertEqual(markup.escape("Tom & Jerry <1080p>"), "Tom &amp; Jerry &lt;1080p&gt;")

    def test_highlight_match_escapes_all_parts(self):
        text = "A&B <S01E01> C&D"
        result = markup.highlight_match(text, byte_span(text, "<S01E01>"), "#5acf36")
        self.assertEqual(
            result,
            'A&amp;B <span background="#5acf36"><b>&lt;S01E01&gt;</b></span> C&amp;D',
        )

    def test_highlight_match_uses_byte_offsets(self):
        text = "Ä S01E01 x"
        result = markup.highlight_match(text, byte_span(text, "S01E01"), "#f31010")
        self.assertEqual(result, 'Ä <span background="#f31010"><b>S01E01</b></span> x')
