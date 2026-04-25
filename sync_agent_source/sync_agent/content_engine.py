import os
import re
from collections import defaultdict
from dateutil.parser import parse
from odf import text, teletype
from odf.opendocument import load, OpenDocumentText

class SegmentedODFHandler:
    TAG_REGEX = r'<\d+\W\d+\W\d+>'

    def parse_to_dict(self, path):
        if not os.path.exists(path): return {}
        try:
            doc = load(path)
            content = "\n".join(teletype.extractText(p) for p in doc.getElementsByType(text.P))
            data = defaultdict(list)
            tags = re.findall(self.TAG_REGEX, content)
            segments = re.split(self.TAG_REGEX, content)[1:]
            for tag, seg in zip(tags, segments):
                dt = parse(tag.strip()[1:-1]).date()
                data[dt].append(seg.strip())
            return data
        except Exception:
            return {}

    def save_combined(self, data, path):
        doc = OpenDocumentText()
        for dt in sorted(data.keys(), reverse=True):
            tag = f"<{dt.month}/{dt.day}/{dt.year}>"
            for seg in data[dt]:
                p = text.P()
                teletype.addTextToElement(p, f"{tag}{seg}")
                doc.text.addElement(p)
        doc.save(path)
