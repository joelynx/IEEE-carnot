"""Read-only: strip HTML to visible text. Usage: python -I html2text.py IN.html OUT.txt"""
import sys
from html.parser import HTMLParser
from pathlib import Path

BLOCK = {"p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "br", "section", "article",
         "header", "footer", "table", "ul", "ol", "dt", "dd", "pre", "summary", "details", "td", "th"}


class P(HTMLParser):
    def __init__(self):
        super().__init__()
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "svg"):
            self.skip += 1
        if tag in BLOCK:
            self.out.append("\n")
        if tag == "a":
            href = dict(attrs).get("href")
            if href and not self.skip:
                self.out.append("")
                self._href = href
        if tag in ("td", "th"):
            self.out.append(" | ")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "svg") and self.skip:
            self.skip -= 1
        if tag in BLOCK:
            self.out.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


p = P()
p.feed(Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace"))
text = "".join(p.out)
lines = [" ".join(l.split()) for l in text.splitlines()]
clean = []
for l in lines:
    if l or (clean and clean[-1]):
        clean.append(l)
Path(sys.argv[2]).write_text("\n".join(clean), encoding="utf-8")
print(sys.argv[2], len(clean), "lines")
