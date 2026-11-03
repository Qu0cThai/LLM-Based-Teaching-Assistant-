from lesson.retriever import retrieve_with_sources
from lesson.planner_subtopics import extract_subtopics

def retrieve_planning_context(topic, chapter, vector_store):
    if not vector_store or not vector_store.data:
        return "", ""

    base_context, _ = retrieve_with_sources(
        topic,
        vector_store,
        top_k=10
    )

    subtopics = extract_subtopics(topic, base_context)
    
    query = topic
    if chapter:
        query = f"{chapter}: {topic}"
    
    expanded_query = query
    if subtopics:
        expanded_query += ", " + ", ".join(subtopics)

    final_context, sources = retrieve_with_sources(
        expanded_query,
        vector_store,
        top_k=20
    )

    return final_context, sources