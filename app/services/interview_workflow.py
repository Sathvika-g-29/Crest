
from langgraph.graph import StateGraph, START, END

from app.models.interview_state import InterviewState
from app.services.interview_generator import generate_interview_question
from app.services.answer_evaluator import evaluate_answer
from app.services.followup_generator import generate_followup_question


def route_start(state: InterviewState):
    if state.get("interview_status") == "completed":
        return "complete"

    if state.get("candidate_answer", "").strip():
        return "evaluate_answer"

    return "generate_question"


def generate_question_node(state: InterviewState):
    question = generate_interview_question(
        skill=state["skill"],
        resume_evidence=state["resume_evidence"],
    )

    return {
        "current_question": question,
        "candidate_answer": "",
        "followup_question": "",
        "next_action": "answer",
        "interview_status": "in_progress",
    }


def evaluate_answer_node(state: InterviewState):
    evaluation = evaluate_answer(
        question=state["current_question"],
        candidate_answer=state["candidate_answer"],
    )

    history = state.get("interview_history", []) + [{
        "question": state["current_question"],
        "answer": state["candidate_answer"],
        "score": evaluation.correctness_score,
        "knowledge_gaps": evaluation.knowledge_gaps,
        "feedback": evaluation.feedback,
    }]

    return {
        "correctness_score": evaluation.correctness_score,
        "knowledge_gaps": evaluation.knowledge_gaps,
        "interview_history": history,
        "next_action": "followup" if evaluation.knowledge_gaps else "continue",
    }


def decide_next_step(state: InterviewState):
    if state.get("interview_status") == "completed":
        return "complete"

    if state.get("knowledge_gaps"):
        return "followup"

    return "generate_question"


def generate_followup_node(state: InterviewState):
    followup = generate_followup_question(
        original_question=state["current_question"],
        candidate_answer=state["candidate_answer"],
        knowledge_gaps=state["knowledge_gaps"],
    )

    return {
        "followup_question": followup,
        "current_question": followup,
        "candidate_answer": "",
        "next_action": "answer",
    }


def complete_node(state: InterviewState):
    return {
        "next_action": "complete",
        "interview_status": "completed",
    }


builder = StateGraph(InterviewState)

builder.add_node("generate_question", generate_question_node)
builder.add_node("evaluate_answer", evaluate_answer_node)
builder.add_node("generate_followup", generate_followup_node)
builder.add_node("complete", complete_node)


# Define where the workflow begins.
builder.add_conditional_edges(
    START,
    route_start,
    {
        "generate_question": "generate_question",
        "evaluate_answer": "evaluate_answer",
        "complete": "complete",
    },
)

# Decide what happens after evaluating an answer.
builder.add_conditional_edges(
    "evaluate_answer",
    decide_next_step,
    {
        "followup": "generate_followup",
        "generate_question": "generate_question",
        "complete": "complete",
    },
)

builder.add_edge("generate_question", END)
builder.add_edge("generate_followup", END)
builder.add_edge("complete", END)

interview_workflow = builder.compile()
