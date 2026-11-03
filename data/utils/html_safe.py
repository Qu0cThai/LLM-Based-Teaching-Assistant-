import html

def safe_html(text: str) -> str:
    return html.escape(text)
