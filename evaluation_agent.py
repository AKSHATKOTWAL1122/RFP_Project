from __future__ import annotations

import os
import time
from typing import List

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI

from models import Criterion, LLMEvaluationOutput

MODEL_NAME = "gemini-2.5-flash"
MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2


class EvaluationError(Exception):
    def __init__(self, supplier_name: str, message: str):
        self.supplier_name = supplier_name
        self.message = message
        super().__init__(f"[{supplier_name}] {message}")


_SYSTEM = (
    "You are an impartial RFP proposal evaluator. Judge only the proposal content "
    "supplied to you. Use only evidence present in the supplied document text — never "
    "invent facts, capabilities, prices, or references that are not written there. If "
    "the document lacks evidence for a criterion, say so and score conservatively.\n\n"
    "Return exactly one result per active criterion listed below — no more, no fewer — "
    "using the given criterion_id values. Keep each score within [0, max_score] for that "
    "criterion. Output JSON only, matching the format instructions.\n\n"
    "{format_instructions}"
)

_HUMAN = (
    "Supplier name: {supplier_name}\n\n"
    "Active criteria (evaluate against each, verbatim inspection guidance):\n"
    "{criteria_block}\n\n"
    "Proposal document text:\n"
    "\"\"\"\n{document_text}\n\"\"\"\n"
)


def _api_key() -> str:
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        raise EvaluationError("<config>", "GEMINI_API_KEY is not set")
    return key


def _criteria_block(criteria: List[Criterion]) -> str:
    lines = []
    for c in criteria:
        lines.append(
            f"- criterion_id={c.criterion_id} | name={c.name} | max_score={c.max_score} | "
            f"guidance: {c.description}"
        )
    return "\n".join(lines)


def _build_chain():
    parser = PydanticOutputParser(pydantic_object=LLMEvaluationOutput)
    prompt = ChatPromptTemplate.from_messages(
        [("system", _SYSTEM), ("human", _HUMAN)]
    ).partial(format_instructions=parser.get_format_instructions())
    model = ChatGoogleGenerativeAI(
        model=MODEL_NAME, temperature=0, google_api_key=_api_key()
    )
    return prompt | model | parser


def evaluate_supplier(
    supplier_name: str, document_text: str, criteria_snapshot: List[Criterion]
) -> LLMEvaluationOutput:
    chain = _build_chain()
    payload = {
        "supplier_name": supplier_name,
        "document_text": document_text,
        "criteria_block": _criteria_block(criteria_snapshot),
    }

    last_exc: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return chain.invoke(payload)
        except Exception as exc:
            last_exc = exc
            if attempt < MAX_ATTEMPTS:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)

    raise EvaluationError(
        supplier_name, f"LLM evaluation failed after {MAX_ATTEMPTS} attempts: {last_exc}"
    )
