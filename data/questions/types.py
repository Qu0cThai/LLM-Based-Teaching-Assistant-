from enum import Enum

class QuestionType(str, Enum):
    MCQ = "mcq"
    SHORT_ANSWER = "short_answer"
    FILL_BLANK = "fill_blank"

    @classmethod
    def from_label(cls, label: str) -> "QuestionType | None":
        mapping = {
            "MCQ": cls.MCQ,
            "Short Answer": cls.SHORT_ANSWER,
            "Fill in the Blank": cls.FILL_BLANK,
        }
        return mapping.get(label)

    @classmethod
    def all(cls):
        return list(cls)
