import re
from llm.ollama_client import ollama_chat
from config import MODEL_PLANNER
from lesson.planner_prompts import PROMPT_LESSON_PLAN
from lesson.planner_retriever import retrieve_planning_context
from lesson.planner_parser import safe_json_parse
from lesson.planner_normalizer import normalize_lesson_plan

def generate_lesson_plan(
    topic,
    chapter,
    duration,
    notes,
    vector_store,
    style="balanced",
    lesson_type="lecture"
):
    context, sources = retrieve_planning_context(
        topic,
        chapter,
        vector_store
    )

    prompt = PROMPT_LESSON_PLAN.format(
        topic=topic,
        chapter=chapter,
        duration=duration,
        notes=notes,
        context=context,
        sources=sources,
        style=style,
        lesson_type=lesson_type
    )

    resp = ollama_chat(MODEL_PLANNER, prompt)

    raw = resp["message"]["content"]

    raw = re.sub(
        r'"\s*\n\s*([^"]+)',
        r' \1',
        raw
    )

    data = safe_json_parse(raw)

    if "error" not in data:
        data = normalize_lesson_plan(data)

    return data

def render_lesson_plan(data: dict) -> str:
    text = f"## {data.get('title','Lesson Plan')}\n\n"
    text += f"**Duration:** {data.get('duration','')}  \n\n"

    text += "### Objectives\n"
    for o in data.get("objectives", []):
        text += f"- {o}\n"

    text += "\n### Materials\n"
    for m in data.get("materials", []):
        text += f"- {m}\n"

    text += "\n### Activities\n"
    for a in data.get("activities", []):
        text += f"**Step {a.get('step')}**: {a.get('description')}\n\n"

    text += "### Assessment\n"
    for a in data.get("assessment", []):
        text += f"- {a}\n"

    text += "\n### Homework\n"
    for h in data.get("homework", []):
        text += f"- {h}\n"

    if not data.get("homework"):
        text += "- No homework assigned\n"
    
    text += "\n### References\n"
    for r in data.get("references", []):
        text += f"- {r}\n"
        
    return text