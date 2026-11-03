import ast

def ensure_list(v, fallback):
    if isinstance(v, list) and v:
        return [str(x).strip() for x in v if str(x).strip()]
    if isinstance(v, str) and v.strip():
        return [v.strip()]
    return fallback

def normalize_lesson_plan(data: dict) -> dict:
    def ensure_list_of_strings(value, fallback):
        def parse_stringified(item):
            if isinstance(item, str):
                item = item.strip()
                if item.startswith('[') and item.endswith(']'):
                    try:
                        parsed = ast.literal_eval(item)
                        if isinstance(parsed, list):
                            return parsed
                    except Exception:
                        pass
            return item

        value = parse_stringified(value)
        
        if isinstance(value, list) and len(value) > 0:
            cleaned = []
            for v in value:
                v = parse_stringified(v)
                
                if isinstance(v, list):
                    for sub_v in v:
                        cleaned.append(str(sub_v))
                elif isinstance(v, dict):
                    if "description" in v:
                        cleaned.append(str(v["description"]))
                    else:
                        cleaned.append(" - ".join(str(x) for x in v.values()))
                else:
                    cleaned.append(str(v))
            return cleaned

        if isinstance(value, dict) and value:
            if "description" in value:
                return [str(value["description"])]
            return [" - ".join(str(v) for v in value.values())]

        if isinstance(value, str) and value.strip():
            return [value]

        return fallback

    BAD_MATERIALS = {"pen", "paper", "computer", "notebook"}

    def clean_materials(materials):
        cleaned = []
        for m in materials:
            m_lower = m.lower()
            if not any(bad in m_lower for bad in BAD_MATERIALS):
                cleaned.append(m)

        if not cleaned:
            return ["Textbook or lecture slides related to the topic"]

        return cleaned
    
    data["objectives"] = ensure_list_of_strings(
        data.get("objectives"),
        ["Understand key concepts of the topic"]
    )

    data["materials"] = clean_materials(
        ensure_list_of_strings(
            data.get("materials"),
            ["Textbook or lecture slides"]
        )
    )

    data["assessment"] = ensure_list_of_strings(
        data.get("assessment"),
        ["Short quiz or class discussion"]
    )

    data["homework"] = ensure_list_of_strings(
        data.get("homework"),
        ["Review the lesson and summarize key points"] 
    )
    
    data["references"] = ensure_list_of_strings(
        data.get("references"),
        ["Extracted from uploaded learning materials"]
    )

    activities = data.get("activities", [])
    fixed_activities = []

    if isinstance(activities, list) and len(activities) > 0:
        for i, a in enumerate(activities, 1):
            if isinstance(a, dict):
                fixed_activities.append({
                    "step": a.get("step", i),
                    "description": str(a.get("description", "")).strip()
                })
            else:
                fixed_activities.append({
                    "step": i,
                    "description": str(a)
                })
    else:
        fixed_activities = [
            {"step": 1, "description": "Introduce the topic"},
            {"step": 2, "description": "Explain key concepts"},
        ]

    data["activities"] = fixed_activities

    return data
