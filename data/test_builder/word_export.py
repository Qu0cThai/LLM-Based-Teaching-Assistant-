import re
from docx import Document
from docx.shared import Pt
from io import BytesIO
import random
from questions.normalize import get_mcq_answer_text
from config import QUESTION_TYPE_ORDER

def strip_mcq_label(text: str) -> str:
    return re.sub(r"^[A-D]\.\s*", "", text).strip()


def save_test_to_word(test, type_order):
    doc = Document()
    doc.add_heading(test["title"], level=1)

    total = len(test["questions"])
    points = max(1, round(100 / total))

    idx = 1
    for qtype in type_order:
        qtype_str = qtype.value if hasattr(qtype, 'value') else str(qtype)
        
        section = [q for q in test["questions"] if q["type"] == qtype_str]
        if not section:
            continue

        if qtype_str == "mcq":
            random.shuffle(section)

        for q in section:
            p = doc.add_paragraph()
            run = p.add_run(f"Q{idx}: {q['question']} ({points} pts)")
            run.bold = True
            run.font.size = Pt(12)

            if qtype_str == "mcq":
                for opt in q.get("options", []):
                    doc.add_paragraph(opt)
            elif qtype_str == "short_answer":
                doc.add_paragraph("\nAnswer: ________________________________________________________\n_________________________________________________________________\n")
            else:
                doc.add_paragraph("Answer: __________")

            idx += 1

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

def save_answer_key_to_word(test):
    doc = Document()
    doc.add_heading(f"ANSWER KEY – {test['title']}", level=1)

    total_questions = len(test["questions"])
    points_per_q = max(1, round(100 / total_questions))

    idx = 1
    for qtype in QUESTION_TYPE_ORDER:
        qtype_str = qtype.value if hasattr(qtype, 'value') else str(qtype)
        
        for q in test["questions"]:
            if q["type"] != qtype_str:
                continue

            p = doc.add_paragraph()
            run = p.add_run(f"Q{idx} ({points_per_q} points): ")
            run.bold = True
            
            if q["type"] == "mcq":
                answer_text = get_mcq_answer_text(q)
                clean_text = strip_mcq_label(answer_text)
                doc.add_paragraph(f"{q.get('answer', '')} — {clean_text}")
            else:
                doc.add_paragraph(str(q.get("answer", "")))

            idx += 1

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

def save_lesson_plan_to_word(data):
    doc = Document()

    doc.add_heading(data.get("title", "Lesson Plan"), 0)

    doc.add_paragraph(f"Duration: {data.get('duration','')}")

    doc.add_heading("Objectives", level=1)
    for o in data.get("objectives", []):
        doc.add_paragraph(o)

    doc.add_heading("Materials", level=1)
    for m in data.get("materials", []):
        doc.add_paragraph(m)

    doc.add_heading("Activities", level=1)
    for a in data.get("activities", []):
        doc.add_paragraph(f"Step {a.get('step')}: {a.get('description')}")

    doc.add_heading("Assessment", level=1)
    for a in data.get("assessment", []):
        doc.add_paragraph(a)

    doc.add_heading("Homework", level=1)
    for h in data.get("homework", []):
        doc.add_paragraph(h)

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf