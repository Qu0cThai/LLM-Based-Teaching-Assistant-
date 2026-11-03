from questions.types import QuestionType

def compute_quota(
    total: int,
    selected_types: list[QuestionType],
) -> dict[QuestionType, int]:

    quota: dict[QuestionType, int] = {}
    if not selected_types or total <= 0:
        return quota
    
    if QuestionType.MCQ in selected_types:
        mcq_count = max(1, total // 2)
        quota[QuestionType.MCQ] = mcq_count
    else:
        mcq_count = 0

    remaining = total - mcq_count

    other_types = [t for t in selected_types if t is not QuestionType.MCQ]

    if not other_types:
        if QuestionType.MCQ in quota:
            quota[QuestionType.MCQ] = total
        return quota

    base = remaining // len(other_types)
    extra = remaining % len(other_types)

    for i, qtype in enumerate(other_types):
        quota[qtype] = base + (1 if i < extra else 0)
        
    return quota

def compute_diff_quota(total: int, dist: dict) -> dict:
    total_pct = sum(dist.values())
    if total_pct == 0:
        return {"Easy": 0, "Medium": total, "Hard": 0}
        
    easy_count = int(round(total * (dist.get("Easy", 0) / total_pct)))
    medium_count = int(round(total * (dist.get("Medium", 0) / total_pct)))
    hard_count = total - easy_count - medium_count
    
    if hard_count < 0:
        medium_count += hard_count
        hard_count = 0
        
    return {"Easy": easy_count, "Medium": medium_count, "Hard": hard_count}