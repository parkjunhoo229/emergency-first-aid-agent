import json

def load_disease_json(path="disease_symptom.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_disease_prompt_string(disease_map):
    lines = []
    for disease, info in disease_map.items():
        level = info.get("emergency_level", "").strip()
        symptoms = info.get("symptoms", [])
        symptom_list = ", ".join(f'"{s}"' for s in symptoms)
        lines.append(f"{disease}: {level}[{symptom_list}]")
    return "\n".join(lines)
