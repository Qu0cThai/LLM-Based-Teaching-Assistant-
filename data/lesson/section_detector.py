import re

def detect_sections(text):
    lines = text.split("\n")

    sections = []
    current_title = "Introduction"
    current_content = []

    def is_heading(line):
        line = line.strip()

        return (
            len(line) < 80 and
            (
                re.match(r'^(chapter|section)\s+\d+', line.lower()) or
                re.match(r'^\d+(\.\d+)*\s+', line) or
                line.isupper()
            )
        )

    for line in lines:
        if not line.strip():
            continue

        if is_heading(line):
            if current_content:
                sections.append({
                    "title": current_title,
                    "content": "\n".join(current_content)
                })

            current_title = line.strip()
            current_content = []
        else:
            current_content.append(line)

    if current_content:
        sections.append({
            "title": current_title,
            "content": "\n".join(current_content)
        })

    return sections