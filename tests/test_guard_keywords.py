import pytest

from csql.nodes.guard import keyword_label

ADVICE = [
    "Should I take metformin for my high blood sugar?",
    "Do I have diabetes if my glucose is 140?",
    "What is the best treatment for hypertension?",
    "What dose of lisinopril should the patient get?",
    "Can I take ibuprofen with warfarin?",
    "Please diagnose me: I have chest pain and dizziness",
    "How can I lower my blood pressure?",
    "Which drug should we give to a 70 year old with kidney failure?",
]
DATA = [
    "How many patients were prescribed metformin?",
    "What is the average age of patients with diabetes?",
    "List the 5 most common conditions.",
    "How many female patients have hypertension?",
    "What is the average claim cost of emergency encounters?",
    "How many patients received a flu vaccine in 2024?",
]


@pytest.mark.parametrize("q", ADVICE)
def test_advice_flagged(q):
    assert keyword_label(q) == "medical_advice"


@pytest.mark.parametrize("q", DATA)
def test_data_questions_pass(q):
    assert keyword_label(q) == "data_question"
