"""Prompt templates shared by the benchmark (glimmer_decide.py) and the API (serve.py).

A trained head is valid only for the exact prompt its features came from, so both sides import
these templates. The name of the template is stored with the head.
"""
SYSTEM_INSPECT = ("You are a visual inspection system on a production line. Answer with one word. "
                  "Reasoning strength: low.")
SYSTEM_GENERIC = "You are a visual decision system. Answer with one word. Reasoning strength: low."

TEMPLATES = {
    # name: (system prompt, question format with {name} = object name, {opt} = option)
    "inspect_defective_v1": (SYSTEM_INSPECT, "Does this {name} have a visible manufacturing defect? Answer yes or no."),
    "inspect_good_v1": (SYSTEM_INSPECT, "Is this {name} in good condition with no defect? Answer yes or no."),
    "inspect_type_v1": (SYSTEM_INSPECT, "Does this {name} show the defect type '{opt}'? Answer yes or no."),
    "inspect_severity_v1": (SYSTEM_INSPECT, "Rate the severity of damage to this {name} on a scale from 0 to 3, "
                            "where 0 is none, 1 is minor, 2 is moderate, and 3 is severe. Answer with one digit."),
}
