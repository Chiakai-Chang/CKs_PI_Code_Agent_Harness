"""Reading view for AX-tree snapshots, tested against real captured pages.

Ported in idea from pi-browser-harness (src/domains/readpage/readability.ts) but
not in method: that implementation captures raw DOM blocks over CDP and guesses
the article body by scoring text density against link density. An accessibility
tree already labels every node's role, so filtering by role is simpler, needs no
in-page script injection, and cannot break on a hostile page.

Measured on the fixtures in tests/fixtures, captured live from the running
camofox server:

  Wikipedia article  8,253 chars   /url plumbing 43.1%, prose 22.9%
  News homepage     34,012 chars   link lines 34.2%, prose 31.7%

and of 57 [eN] refs on the Wikipedia page, ZERO sat on a prose line — dropping
the interactive scaffolding costs no readable content.
"""

import json
import os
import re
import shutil
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD = os.path.join(ROOT, "pi-extensions", "stealth-web-bridge", "readability.ts")
FIXTURES = os.path.join(ROOT, "tests", "fixtures")


def _node_major():
    if not shutil.which("node"):
        return 0
    try:
        out = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=30).stdout
    except Exception:
        return 0
    m = re.match(r"v(\d+)", out.strip())
    return int(m.group(1)) if m else 0


NODE_OK = _node_major() >= 22


def extract(fixture_or_text, is_text=False):
    driver = os.path.join(ROOT, "tests", ".tmp_read_driver.mjs")
    payload = os.path.join(ROOT, "tests", ".tmp_read_input.txt")
    url = "file:///" + MOD.replace("\\", "/")
    text = fixture_or_text if is_text else open(
        os.path.join(FIXTURES, fixture_or_text), encoding="utf-8").read()
    # newline="" so Windows does not rewrite \n as \r\n on the way to node —
    # that alone made the fail-open assertion compare CRLF against LF.
    with open(payload, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    with open(driver, "w", encoding="utf-8") as f:
        f.write(
            'import { readFileSync } from "node:fs";\n'
            'import { extractReadable, formatReadingView } from %s;\n'
            'const s = readFileSync(process.argv[2], "utf-8");\n'
            'const r = extractReadable(s);\n'
            'process.stdout.write(JSON.stringify({...r, view: formatReadingView("[hdr]", r)}));\n'
            % json.dumps(url))
    try:
        p = subprocess.run(["node", driver, payload], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", cwd=ROOT, timeout=120)
        if p.returncode != 0:
            raise AssertionError("node driver failed:\n%s\n%s" % (p.stdout, p.stderr))
        return json.loads(p.stdout)
    finally:
        for x in (driver, payload):
            if os.path.exists(x):
                os.remove(x)


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestArticlePage(unittest.TestCase):
    def setUp(self):
        self.r = extract("ax-wikipedia-article.txt")

    def test_cuts_the_page_substantially(self):
        self.assertLess(self.r["readableChars"], self.r["originalChars"] * 0.40,
                        "an article page should lose most of its chrome")

    def test_drops_url_plumbing_and_element_refs(self):
        """An article's links are inline prose links; their addresses are the
        43.1% of plumbing this filter exists to remove. Measured on this fixture:
        keeping headline URLs costs 0.0% here, because an article has none."""
        self.assertNotIn("/url:", self.r["text"])
        self.assertIsNone(re.search(r"\[e\d+\]", self.r["text"]))

    def test_drops_whole_navigation_subtrees_not_just_the_container(self):
        """Line-by-line filtering kept the CHILDREN of a dropped navigation
        node: the first run returned 'Donate', 'Create account', 'Log in',
        'Article', 'Talk' as page content. This is pi-browser-harness's
        `inBoilerplate` idea — an ancestor being nav/banner condemns the whole
        subtree — applied through indentation."""
        for junk in ("Donate", "Create account", "Log in", "Main menu", "Search Wikipedia"):
            self.assertNotIn(junk, self.r["text"], "navigation leaked: %s" % junk)

    def test_keeps_the_article(self):
        self.assertIn("Accessibility tree", self.r["text"])
        self.assertIn("From Wikipedia", self.r["text"])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestLinkHeavyIndexPage(unittest.TestCase):
    """On an index or search-results page the headlines ARE links. Prose-only
    filtering would hand back a news site with its headlines removed —
    measured at 31.5% of the page, versus 63.5% when link titles are kept."""

    def setUp(self):
        self.r = extract("ax-news-homepage.txt")

    def test_keeps_headlines(self):
        titles = re.findall(r'- link "', self.r["text"])
        self.assertGreater(len(titles), 20, "headlines were stripped from an index page")

    def test_still_reduces_the_page(self):
        self.assertLess(self.r["readableChars"], self.r["originalChars"])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestCitableAddressesSurvive(unittest.TestCase):
    """A headline's address is the one thing a researcher has to keep.

    Measured across five runs of a market-survey brief: 632 web_searches returned
    zero URLs, and the model responded by reconstructing addresses from link text
    — one run cited 14 pages having opened 8. The tool's own description promised
    "result titles, snippets, and URLs" and then told the model to "call web_open
    on the 1-3 most relevant result URLs" it had never been given.

    A `/url:` inside a link block that also carries a heading is a result link. A
    `/url:` with no heading under it is navigation. Measured on the fixtures:

        wikipedia article   /url all 43.1%   headline-only 0.0%   (0 of 44)
        docs site           /url all 11.4%   headline-only 0.0%   (0 of 158)
        github issue        /url all 28.0%   headline-only 0.0%   (0 of 110)
        news homepage       /url all 16.8%   headline-only 5.3%   (42 of 112)

    The 43.1% that motivated dropping them is untouched: articles have no
    heading-links. Index pages pay 5.3% and get their addresses back.
    """

    def setUp(self):
        self.r = extract("ax-news-homepage.txt")

    def test_headline_addresses_are_kept(self):
        self.assertIn("/url:", self.r["text"],
                      "an index page's result addresses are its payload")

    def test_navigation_addresses_are_still_dropped(self):
        """`- /url: "#bbc-main"` and `- /url: /` are plumbing with no headline."""
        self.assertNotIn('/url: "#bbc-main"', self.r["text"])

    def test_it_costs_a_bounded_amount(self):
        """Cheap enough not to reopen the decision that dropped them."""
        self.assertLess(self.r["readableChars"], self.r["originalChars"] * 0.70)

    def test_an_article_pays_nothing(self):
        """The case the original measurement was taken on must not regress."""
        article = extract("ax-wikipedia-article.txt")
        self.assertNotIn("/url:", article["text"])


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestFailOpen(unittest.TestCase):
    def test_widget_only_page_returns_the_original(self):
        """Returning an empty 'article' would read as a successfully-read blank
        page — the same failure that had web_snapshot handing back
        '(empty snapshot)' as a success six turns in a row."""
        widgets = "\n".join('  - button "Btn%d" [e%d]' % (i, i) for i in range(40))
        r = extract(widgets, is_text=True)
        self.assertEqual(r["text"], widgets)

    def test_empty_input_does_not_crash(self):
        r = extract("", is_text=True)
        self.assertEqual(r["text"], "")


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestReadingViewFooter(unittest.TestCase):
    def test_tells_the_model_how_to_reach_element_refs(self):
        """The view removes [eN] refs on purpose, so it has to say where they
        are — otherwise clicking becomes unreachable rather than one call away."""
        r = extract("ax-wikipedia-article.txt")
        self.assertIn("web_snapshot", r["view"])
        self.assertIn("reading view:", r["view"])


class TestBridgeWiring(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(ROOT, "pi-extensions", "stealth-web-bridge", "index.ts"),
                  encoding="utf-8") as f:
            self.src = f.read()

    def test_reading_view_is_the_default_for_search_and_open(self):
        self.assertEqual(self.src.count("renderPage(tabId, snap, params.raw)"), 2)

    def test_raw_opt_out_exists(self):
        self.assertIn("RAW_PARAM", self.src)
        self.assertEqual(self.src.count("raw: RAW_PARAM"), 2)

    def test_every_relative_import_has_a_shipped_sibling(self):
        """A bridge importing ./x.js needs x.ts next to it in the SOURCE tree,
        because restore.py copytree's the directory wholesale. Add an import
        without the file and the bridge dies at load time with every tool it
        registers — which for stealth-web is all web access."""
        import glob
        for idx in glob.glob(os.path.join(ROOT, "pi-extensions", "*", "index.ts")):
            with open(idx, encoding="utf-8") as f:
                src = f.read()
            base = os.path.dirname(idx)
            for spec in re.findall(r'from\s+"\./([A-Za-z0-9_.-]+)\.js"', src):
                self.assertTrue(
                    os.path.exists(os.path.join(base, spec + ".ts")),
                    "%s imports ./%s.js but %s.ts is not in the bridge directory"
                    % (os.path.relpath(idx, ROOT), spec, spec),
                )

    def test_web_snapshot_still_returns_the_full_tree(self):
        """web_snapshot is the tool you call before clicking; stripping refs
        there would remove the capability rather than defer it."""
        snap_block = self.src[self.src.index('name: "web_snapshot"'):]
        snap_block = snap_block[:snap_block.index("});")]
        self.assertNotIn("renderPage", snap_block)
        self.assertNotIn("extractReadable", snap_block)


@unittest.skipUnless(NODE_OK, "node >= 22 required")
class TestAcrossPageLayouts(unittest.TestCase):
    """Role-based filtering could plausibly misfire on layouts unlike the two it
    was built against. These fixtures were captured live through the running
    camofox server: a docs page, a GitHub issue list (app shell) and a Hacker
    News thread (table-based, no semantic roles to speak of).

    The assertion is deliberately not "reduces by N%" — a filter that returned
    nothing would score wonderfully on that. What matters is that the reduction
    is real but not degenerate, and that the page's actual content survives.
    """

    LAYOUTS = [
        ("ax-wikipedia-article.txt", ["Accessibility tree"]),
        ("ax-news-homepage.txt", []),
        ("ax-docs-site.txt", ["json", "serialize", "JSONDecoder"]),
        ("ax-github-issue.txt", ["Issues"]),
        ("ax-forum-thread.txt", ["Y Combinator"]),
    ]

    def test_every_layout_reduces_without_collapsing(self):
        for name, _ in self.LAYOUTS:
            if not os.path.exists(os.path.join(FIXTURES, name)):
                continue
            r = extract(name)
            ratio = r["readableChars"] / r["originalChars"]
            self.assertLess(ratio, 0.95, "%s barely reduced (%.0f%%)" % (name, ratio * 100))
            self.assertGreater(ratio, 0.05, "%s collapsed to almost nothing (%.0f%%)" % (name, ratio * 100))

    def test_no_layout_leaks_refs_or_navigation_urls(self):
        """Element refs still go everywhere. Addresses go except where they are
        the payload.

        This used to assert no `/url:` survived anywhere, which is what made
        research impossible to source: 632 web_searches across five runs returned
        zero URLs and the model reconstructed addresses from link text. A `/url:`
        under a heading is a result link and stays; one without is navigation and
        still goes.
        """
        for name, _ in self.LAYOUTS:
            if not os.path.exists(os.path.join(FIXTURES, name)):
                continue
            r = extract(name)
            self.assertIsNone(re.search(r"\[e\d+\]", r["text"]), name)
            for line in r["text"].splitlines():
                if "/url:" not in line:
                    continue
                self.assertNotRegex(
                    line, r'/url:\s*"?[#/]"?\s*$',
                    "%s kept a navigation address: %s" % (name, line.strip()))

    def test_content_survives_on_every_layout(self):
        for name, markers in self.LAYOUTS:
            path = os.path.join(FIXTURES, name)
            if not os.path.exists(path) or not markers:
                continue
            with open(path, encoding="utf-8") as f:
                original = f.read()
            r = extract(name)
            for marker in markers:
                if marker.lower() not in original.lower():
                    continue  # never in the capture; not the filter's doing
                self.assertIn(marker.lower(), r["text"].lower(),
                              "%s lost %r" % (name, marker))


if __name__ == "__main__":
    unittest.main()
