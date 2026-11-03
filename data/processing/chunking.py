import re

def is_code_line(line: str) -> bool:
    patterns = [
        r"\{|\}",
        r";$",
        r"==|!=|<=|>=",
        r"#include|using|import",
    ]
    return any(re.search(p, line) for p in patterns)

def chunk_text_semantic(text, max_text_lines=8):
    lines = text.split("\n")

    chunks = []
    current = []
    in_code = False

    for line in lines:
        if is_code_line(line):
            if not in_code:
                if current:
                    chunks.append("\n".join(current))
                    current = []
                in_code = True
            current.append(line)
        else:
            if in_code:
                chunks.append("<CODE>\n" + "\n".join(current) + "\n</CODE>")
                current = []
                in_code = False
            current.append(line)

            if len(current) >= max_text_lines:
                chunks.append("\n".join(current))
                current = []

    if current:
        if in_code:
            chunks.append("<CODE>\n" + "\n".join(current) + "\n</CODE>")
        else:
            chunks.append("\n".join(current))

    return [c.strip() for c in chunks if c.strip()]

def chunk_document(text: str):
    return chunk_text_semantic(text)