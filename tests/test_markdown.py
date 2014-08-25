import os
from tempfile import TemporaryDirectory
from unittest import TestCase

from oxalis.converters.markdown import MarkdownConverter


class TestMarkdownConverter(TestCase):
    def test_match(self):
        self.assertTrue(MarkdownConverter.matches("test.md"))
        self.assertTrue(MarkdownConverter.matches("test.markdown"))
        self.assertTrue(MarkdownConverter.matches("complex.test.markdown"))
        self.assertFalse(MarkdownConverter.matches("test.txt"))
        self.assertFalse(MarkdownConverter.matches("test.html"))
        self.assertFalse(MarkdownConverter.matches("test"))
        self.assertFalse(MarkdownConverter.matches("markdown"))

    def test_target(self):
        mc = MarkdownConverter("/tmp/site", "dir/test.md")
        self.assertEqual(mc.target(), "dir/test.html")

    def test_convert(self):
        with TemporaryDirectory() as tempdir:
            # Prepare test files
            with open(os.path.join(tempdir, "test.md"), 'w') as f:
                f.write("# Hello\n")
            with open(os.path.join(tempdir, "meta.md"), 'w') as f:
                f.write("Title: title\nTemplate: other\n\n# Hello\n")
            templates_path = os.path.join(tempdir, "_templates")
            os.mkdir(templates_path)
            with open(os.path.join(templates_path, "default.html"), 'w') as f:
                f.write("Default: {{ content }}")
            with open(os.path.join(templates_path, "other.html"), 'w') as f:
                f.write("Other {{ title }}: {{ content }}")

            # Without metadata
            mc = MarkdownConverter(tempdir, "test.md")
            mc.convert()
            with open(os.path.join(tempdir, "test.html")) as f:
                self.assertEqual(f.read(), "Default: <h1>Hello</h1>")

            # With metadata
            mc = MarkdownConverter(tempdir, "meta.md")
            mc.convert()
            with open(os.path.join(tempdir, "meta.html")) as f:
                self.assertEqual(f.read(), "Other title: <h1>Hello</h1>")
