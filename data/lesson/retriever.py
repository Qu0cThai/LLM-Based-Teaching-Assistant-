def retrieve_with_sources(query, vector_store, top_k=20):
    results = vector_store.search(query, top_k=top_k)

    seen_sources = set()
    selected = []
    selected_texts = set() 

    for r in results:
        if r["source"] not in seen_sources:
            selected.append(r)
            seen_sources.add(r["source"])
            selected_texts.add(r["text"]) 

    for r in results:
        if len(selected) >= 10:
            break
        if r["text"] not in selected_texts: 
            selected.append(r)
            selected_texts.add(r["text"])

    context = "\n\n".join(r["text"] for r in selected)
    sources = "\n".join(r["source"] for r in selected)

    return context, sources