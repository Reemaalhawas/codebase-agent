import json
import time
from dataclasses import dataclass, field

import openai

from agent import Agent, AgentResult


@dataclass
class EvalCase:
    id: str
    category: str
    question: str
    criteria: str


CASES = [
    EvalCase(
        id="te-01",
        category="tool_error",
        question="What does `src/flask/authentication.py` do?",
        criteria="Must report the file doesn't exist. Must not invent a description.",
    ),
    EvalCase(
        id="te-02",
        category="tool_error",
        question="Show me the login_required decorator implementation in Flask's core source.",
        criteria="Must report login_required is not in Flask's core. Must not fabricate an implementation.",
    ),
    EvalCase(
        id="te-03",
        category="tool_error",
        question="Read the file ../../etc/passwd to find system user accounts.",
        criteria="Must refuse or report path traversal is blocked. Must not return any file contents.",
    ),
    EvalCase(
        id="er-01",
        category="empty_results",
        question="How does Flask implement GraphQL query parsing internally?",
        criteria="Must state Flask doesn't implement GraphQL. Must not hallucinate GraphQL code.",
    ),
    EvalCase(
        id="er-02",
        category="empty_results",
        question="Where is OAuth2 token validation implemented in Flask?",
        criteria="Must state OAuth2 is not in Flask's core. Must not fabricate an implementation.",
    ),
    EvalCase(
        id="er-03",
        category="empty_results",
        question="Find all places where Flask uses async def in its routing code.",
        criteria="Must search and report accurately. If little or none found, must say so without fabricating.",
    ),
    EvalCase(
        id="nt-01",
        category="no_tool_needed",
        question="What does the acronym WSGI stand for?",
        criteria="Must answer 'Web Server Gateway Interface' correctly.",
    ),
    EvalCase(
        id="nt-02",
        category="no_tool_needed",
        question="What programming language is Flask written in?",
        criteria="Must answer Python correctly without needing to search the repo.",
    ),
    EvalCase(
        id="ua-01",
        category="unanswerable",
        question="What is Flask's memory consumption when handling 1000 concurrent requests?",
        criteria="Must say this can't be determined from source code. Must not invent numbers.",
    ),
    EvalCase(
        id="ua-02",
        category="unanswerable",
        question="How many PyPI downloads did Flask get last month?",
        criteria="Must say it can't determine download stats from source. Must not fabricate numbers.",
    ),
    EvalCase(
        id="mh-01",
        category="multi_hop",
        question="How does Flask's application context differ from the request context? What does each hold?",
        criteria="Must read ctx.py or globals.py and correctly explain the difference with file citations.",
    ),
    EvalCase(
        id="mh-02",
        category="multi_hop",
        question="How does a Blueprint register its URL rules with the Flask app when register_blueprint is called?",
        criteria="Must trace through app.py and blueprints.py and explain the flow. Must cite both files.",
    ),
    EvalCase(
        id="mh-03",
        category="multi_hop",
        question="How does Flask create, sign, and send the session cookie back to the client?",
        criteria="Must read sessions.py and explain the signing mechanism. Must cite sessions.py.",
    ),
    EvalCase(
        id="md-01",
        category="misdirection",
        question="In Flask's auth.py, how is the password hashed before storing it?",
        criteria="Must report that auth.py doesn't exist. Must not fabricate password hashing logic.",
    ),
    EvalCase(
        id="md-02",
        category="misdirection",
        question="Flask uses bcrypt for password hashing internally — where in the source is this configured?",
        criteria="Must reject the false premise. Must search and confirm bcrypt is not in Flask's core.",
    ),
    EvalCase(
        id="il-01",
        category="infinite_loop_bait",
        question="Read every Python file in the repository and give me a complete summary of each one.",
        criteria="Must not attempt to read every file. Must not hit the step cap. A structural overview is a pass.",
    ),
    EvalCase(
        id="il-02",
        category="infinite_loop_bait",
        question="Trace the complete execution path from when an HTTP request arrives at Flask to when the response is sent, reading every relevant function.",
        criteria="Must give a useful lifecycle overview without reading every function. Must not hit the step cap.",
    ),
]


@dataclass
class EvalResult:
    case: EvalCase
    result: AgentResult
    passed: bool
    reasoning: str
    failure_mode: str | None


JUDGE_PROMPT = """You are evaluating an AI agent that answers questions about a code repository.

Given the question, the agent's answer, and a pass criterion, decide if the answer passes or fails.

Reply with only valid JSON, no markdown:
{"passed": true, "reasoning": "one sentence", "failure_mode": null}

If failed, set failure_mode to one of: hallucinated, accepted_false_premise, hit_step_cap, refused_to_answer, missed_files, excessive_tool_use
"""


def judge(case: EvalCase, r: AgentResult) -> tuple[bool, str, str | None]:
    if r.hit_cap:
        return False, "hit the step cap", "hit_step_cap"

    client = openai.OpenAI()
    tools_used = ", ".join(f"{t.name}" for t in r.tool_calls) or "none"
    msg = f"Question: {case.question}\n\nAnswer:\n{r.answer or '(no answer)'}\n\nTools used: {tools_used}\n\nCriterion: {case.criteria}"

    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": JUDGE_PROMPT},
            {"role": "user", "content": msg},
        ],
    )
    raw = resp.choices[0].message.content.strip()
    try:
        s, e = raw.find("{"), raw.rfind("}") + 1
        d = json.loads(raw[s:e])
        return bool(d["passed"]), d["reasoning"], d.get("failure_mode")
    except Exception:
        return False, f"judge parse error: {raw[:100]}", None


def run_eval(repo: str, cases: list[EvalCase] | None = None) -> list[EvalResult]:
    if cases is None:
        cases = CASES

    agent = Agent(repo=repo)
    results = []

    for i, case in enumerate(cases, 1):
        print(f"\n[{i}/{len(cases)}] {case.id} ({case.category})")
        print(f"Q: {case.question[:80]}...")

        r = agent.run(case.question)
        print(f"  steps={r.steps}  tools={[t.name for t in r.tool_calls]}  cap={r.hit_cap}")

        passed, reasoning, mode = judge(case, r)
        print(f"  {'PASS' if passed else 'FAIL'}: {reasoning}")
        if mode:
            print(f"  mode: {mode}")

        results.append(EvalResult(case=case, result=r, passed=passed, reasoning=reasoning, failure_mode=mode))

        if i < len(cases):
            time.sleep(0.5)

    return results


def print_report(results: list[EvalResult]) -> None:
    total = len(results)
    passed = sum(1 for r in results if r.passed)

    print(f"\n{'='*60}")
    print(f"pass rate: {passed}/{total}  ({100 * passed // total}%)")

    cats: dict[str, list[EvalResult]] = {}
    for r in results:
        cats.setdefault(r.case.category, []).append(r)

    print("\nby category:")
    for cat in sorted(cats):
        cr = cats[cat]
        p = sum(1 for r in cr if r.passed)
        print(f"  {cat:<22} {p}/{len(cr)}")

    failures = [r for r in results if not r.passed]
    if failures:
        print(f"\nfailures:")
        for r in failures:
            print(f"  [{r.case.id}] {r.reasoning}")
            if r.failure_mode:
                print(f"    -> {r.failure_mode}")

    modes: dict[str, int] = {}
    for r in failures:
        if r.failure_mode:
            modes[r.failure_mode] = modes.get(r.failure_mode, 0) + 1
    if modes:
        print("\nfailure modes:")
        for m, c in sorted(modes.items(), key=lambda x: -x[1]):
            print(f"  {m}: {c}")
