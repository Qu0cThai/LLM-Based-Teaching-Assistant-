def chunk_sections(sections, chunk_size=300):
    chunks = []

    for sec in sections:
        words = sec["content"].split()

        for i in range(0, len(words), chunk_size):
            chunk_text = " ".join(words[i:i+chunk_size])

            chunks.append({
                "text": chunk_text,
                "source": sec["title"]
            })

    return chunks