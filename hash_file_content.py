import hashlib
import sys

from odf import text, teletype
from odf.opendocument import load


def text_hash(path: str) -> str:
    """Hash of an .odt file's extracted text, independent of zip/XML metadata.

    Example:
        text_hash("diary.odt")
        # -> "3a7bd3e2360a3d..."
    """
    doc = load(path)
    content = "\n".join(teletype.extractText(p) for p in doc.getElementsByType(text.P))
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    for path in sys.argv[1:]:
        print(f"{text_hash(path)}  {path}")