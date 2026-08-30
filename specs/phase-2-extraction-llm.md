# Phase 2 — Document & LLM

Files: `document_tool.py`, `evaluation_agent.py`

## Scope

Extract text from a supplier's PDF and get a structured, LLM-generated evaluation of it against the run's frozen criteria snapshot. No validation/normalization business rules yet (that's Phase 3) — this phase just needs the raw parsed object to come back reliably shaped. These are two separate files, each scoped to one brief-named component (Document Tool, Evaluation Agent) — do not merge their logic.

## Pre-requisite: Data Preparation Checklist

Before smoke-testing this phase, verify the user's supplied PDFs (`data/sample_pdfs/`) against the brief's requirements (see `PLAN.md`'s Data Preparation Checklist):
- 4 suppliers matching the required profiles (Apex Systems, BrightPath Tech, NexaWorks, Orbit Digital) with their specified strengths/weaknesses
- Each proposal contains: executive summary, proposed solution/implementation approach, timeline/team/milestones, price table with assumptions, security/compliance/risk controls, support model + experience + references

Do not treat arbitrary PDFs as satisfying this deliverable without checking.

## Deliverables

### `document_tool.py`
- PDF text extraction using PyMuPDF only (no pypdf fallback). Raises a typed error (e.g. `DocumentExtractionError`) carrying the supplier name, on empty/corrupted/unreadable PDFs — caught later per-supplier in the orchestrator (Phase 4), not here.
- Nothing else in this file — no LLM calls, no validation logic.

### `evaluation_agent.py`
- LangChain evaluation chain:
  - `ChatPromptTemplate` with input variables: supplier name, extracted document text, and the **run's frozen criterion snapshot** (id, name, description, max_score for each active criterion) — passed in by the orchestrator, not re-fetched from the DB here
  - `PydanticOutputParser(pydantic_object=LLMEvaluationOutput)` — its `get_format_instructions()` output is injected into the prompt
  - `ChatGoogleGenerativeAI(model="gemini-2.5-flash")` as the chat model
  - Chain composed as `prompt | model | parser`
  - Bounded retry on transient API/parse errors (not infinite)
- Prompt must explicitly instruct the model to:
  - Use only evidence present in the supplied document text — never invent facts
  - Return exactly one result per active criterion listed, no more, no fewer
  - Keep each score within `[0, max_score]` for that criterion
  - Output JSON only, matching the parser's format instructions
- Each criterion's `description` is injected **verbatim** from the DB (the brief's exact inspection-guidance wording) — this directly matters for the "PDF extraction & prompting" rubric line (evidence-grounded, dynamic criteria).

## Expected output shape (matches the brief)

```json
{
  "supplier_name": "Apex Systems",
  "criteria": [{"criterion_id": 1, "score": 8, "max_score": 10, "justification": "...", "evidence": "..."}],
  "risks": ["..."],
  "overall_summary": "..."
}
```

## Done-check

Manual smoke test: feed one verified supplier PDF through `document_tool.py` then `evaluation_agent.py` in sequence, confirm a parsed `LLMEvaluationOutput` object comes back matching the expected shape, with one entry per active criterion.
