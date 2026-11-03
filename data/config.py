import os
from questions.types import QuestionType

MODEL_FAST = "qwen2.5-coder:3b"
EMBED_MODEL = "mxbai-embed-large"
MODEL_PLANNER = "qwen2.5-coder:3b"

STOPWORDS = {
    "what", "does", "do", "is", "are", "the", "a", "an",
    "in", "of", "to", "for", "with", "when", "how", "by", "and", "or",
    "meant", "mean", "term", "refer", "refers", "purpose", 
    "significance", "concept", "represent", "represents", "stand", "stands",
    "describe", "described", "imply", "implies", "primarily", "focus"
}

QUESTION_TYPE_LABELS = {
    QuestionType.MCQ: "Multiple Choice Questions",
    QuestionType.SHORT_ANSWER: "Short Answer Questions",
    QuestionType.FILL_BLANK: "Fill in the Blank Questions",
}

QUESTION_TYPE_ORDER = [
    QuestionType.MCQ,
    QuestionType.SHORT_ANSWER,
    QuestionType.FILL_BLANK,
]
