import os
import re
from collections import defaultdict

from dateutil.parser import parse as parse_date
from loguru import logger
from odf import text, teletype
from odf.opendocument import load, OpenDocumentText


def normalize(s: str) -> str:
    """Normalize a segment for similarity comparison.

    Strips leading date-tag tokens, replaces non-word/non-space chars with
    spaces, lowercases, and collapses whitespace. This ensures minor
    punctuation differences don't inflate distance between near-duplicates.

    Example:
        normalize("<1/1/2024>  Hello, world!")
        # -> "hello world"
    """
    cleaned = re.sub(r'^\s*<.{1,20}>|[^\w ]', ' ', str(s).strip().lower())
    return re.sub(r'\s+', ' ', cleaned).strip()


class SegmentedODFHandler:
    """Read and write .odt files structured with <M/D/YYYY> date-tag headers.

    Format: a flat sequence of paragraphs, each opening with a date tag like
    <1/15/2024>. Multiple paragraphs may share the same date. The in-memory
    representation is {date: [segment, ...]}.

    Example:
        h = SegmentedODFHandler()
        data = h.parse("diary.odt")
        data[date(2024, 1, 15)]
        # -> ["Went to the farmer's market.", "Finished the book."]
    """

    TAG_REGEX = r'<\d+\W\d+\W\d+>'

    def parse(self, path: str) -> dict:
        """Return {date: [segment, ...]} for the given .odt file.

        Returns {} if the file is missing or unparseable (logs a warning).
        """
        if not os.path.exists(path):
            return {}
        try:
            doc = load(path)
            content = "\n".join(
                teletype.extractText(p) for p in doc.getElementsByType(text.P)
            )
            data = defaultdict(list)
            tags = re.findall(self.TAG_REGEX, content)
            segments = re.split(self.TAG_REGEX, content)[1:]
            for tag, seg in zip(tags, segments):
                # Normalise newlines and strip whitespace; skip blank segments.
                seg = re.sub(r'\n+', '\n', seg.strip())
                if seg:
                    data[parse_date(tag.strip()[1:-1]).date()].append(seg)
            return data
        except Exception as e:
            logger.warning("Could not parse {}: {}", path, e)
            return {}

    def save(self, data: dict, path: str) -> None:
        """Write {date: [segment, ...]} to a segmented .odt file.

        Each (date, segment) pair becomes one paragraph: <M/D/YYYY>segment.
        Empty or whitespace-only segments are skipped.
        """
        doc = OpenDocumentText()
        for dt in sorted(data.keys(), reverse=True):
            tag = f"<{dt.month}/{dt.day}/{dt.year}>"
            for seg in data[dt]:
                seg = re.sub(r'\n+', '\n', seg.strip())
                if not seg:
                    continue
                p = text.P()
                teletype.addTextToElement(p, f"{tag}{seg}")
                doc.text.addElement(p)
        doc.save(path)
