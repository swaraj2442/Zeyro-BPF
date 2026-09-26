"""Trade Sentinel chat agent (Groq). Narrates computed investigation steps and answers analyst questions."""
import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

import requests

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
# Each model has its own rate-limit bucket on Groq, so falling back spreads load.
MODELS = [m for m in [os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b"), "openai/gpt-oss-20b"] if m]
SYSTEM_PROMPT = Path(__file__).parent.joinpath("trade_sentinel_prompt.md").read_text()

ADVANCE_WORDS = re.compile(r"^\s*(next|continue|go on|proceed|ok(ay)?|yes|sure|keep going|move on|what'?s next|then\??|go)\b", re.I)

_cache: Dict[tuple, Dict] = {}
_lock = threading.Lock()


class AgentUnavailable(Exception):
    pass


def _call_groq(messages: List[Dict], json_mode: bool = False, max_tokens: int = 700) -> Dict:
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise AgentUnavailable("GROQ_API_KEY not set")
    last_err = None
    for model in MODELS:
        body = {"model": model, "messages": messages, "temperature": 0.2,
                "max_completion_tokens": max_tokens, "reasoning_effort": "low", "include_reasoning": False}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        try:
            resp = requests.post(GROQ_URL, headers={"Authorization": f"Bearer {key}"}, json=body, timeout=25)
        except requests.RequestException as exc:
            last_err = str(exc)
            continue
        if resp.status_code == 429:
            last_err = f"rate limited on {model}"
            continue
        if resp.status_code >= 400:
            last_err = f"{model}: HTTP {resp.status_code} {resp.text[:200]}"
            continue
        content = resp.json()["choices"][0]["message"]["content"] or ""
        if content.strip():
            return {"content": content.strip(), "model": model}
        last_err = f"{model}: empty response"
    raise AgentUnavailable(last_err or "no model available")


def _step_payload(case: Dict, step: Dict, index: int, total: int) -> str:
    return (f"Case: {case['name']} ({case['location']}, {case['business']}). "
            f"Step {index + 1} of {total}: {step['title']}.\nFindings:\n{json.dumps(step['findings'], indent=1)}")


# ---------------------------------------------------------------------------------------
# Offline narration, built from the same computed findings, used only if Groq is unreachable
# ---------------------------------------------------------------------------------------

def offline_narration(step: Dict) -> str:
    f, k = step["findings"], step["key"]
    if k == "profile":
        return (f"{f['company']} is a {f['business'].lower()} based in {f['location']}. It has financed "
                f"{f['invoices_financed']} invoices worth **{f['total_financed']}** ({f['financed_vs_declared']} of its declared "
                f"annual volume) through {', '.join(f['financiers_used'])}.")
    if k == "financing":
        split = ", ".join(f"{n}: {c}" for n, c in f["financier_split"].items())
        return f"Pulled the financing history ({f['showing']}). Requests by financier: {split}."
    if k == "duplicates":
        if not f["matches"]:
            return f"Checked all {f['invoices_checked']} invoices across every financier. **No invoice was financed twice.**"
        m = f["matches"][0]
        return (f"**Same invoice financed twice.** {m['first_submission']}; then {m['second_submission']}, "
                f"{m['days_apart']} days later. Matched because: {m['how_matched']}. "
                f"The second financier paid out {m['second_financier_paid_out']}.")
    if k == "loop":
        if not f["loops"]:
            return f"Traced {f['sale_records_checked']} sale records. **No closed trading loop**: goods reach real outside buyers."
        l = f["loops"][0]
        return (f"**Goods are moving in a circle:** {l['route']}. They went round {l['times_goods_went_round']} times, "
                f"cycling {l['invoice_value_cycled']} of invoices with {l['value_growth_first_to_last_round']} value growth, "
                f"and {l['sales_to_buyers_outside_the_loop']} sales to anyone outside the loop.")
    if k == "buyer":
        c = f["checks"][0] if f["checks"] else {}
        if "financier_left_unpaid" in c:
            return (f"{c['buyer']} received one shipment ({c['goods_value']}) but {c['total_financing_raised']} was raised on it. "
                    f"The buyer paid {'; '.join(c['buyer_paid'])}. **{', '.join(c['financier_left_unpaid'])} will not be repaid.**")
        if "payers_inside_the_loop" in c:
            return (f"Every payment came from inside the loop ({c['payers_inside_the_loop']} payer(s)), "
                    f"**{c['payers_outside_the_loop']} from outside**. There's no real end customer.")
        return (f"{c.get('invoices_settled_by_buyer', 0)} of {c.get('invoices_with_sale_records', 0)} invoices were paid by "
                f"{c.get('distinct_buyers', 0)} different buyers. **Money flows like genuine trade.**")
    return (f"Risk score **{f['risk_score']}** ({f['risk_band']}). Fraud patterns: {', '.join(f['fraud_patterns'])}. "
            f"Money at risk: {f['money_at_risk']}. Recommendation: {f['recommended_action']}.")


# ---------------------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------------------

def narrate(version: int, case: Dict, steps: List[Dict], index: int) -> Dict:
    key = ("narrate", version, case["id"], index)
    with _lock:
        if key in _cache:
            return {**_cache[key], "cached": True}
    step = steps[index]
    try:
        out = _call_groq([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _step_payload(case, step, index, len(steps)) + "\n\nExplain this step to the analyst."},
        ])
        result = {"reply": out["content"], "source": "live", "model": out["model"]}
        with _lock:
            _cache[key] = result
    except AgentUnavailable as exc:
        result = {"reply": offline_narration(step), "source": "offline", "model": None, "error": str(exc)}
    return {**result, "cached": False}


def answer(version: int, case: Dict, steps: List[Dict], index: int, question: str, history: List[Dict]) -> Dict:
    """Answer a free-form question. If the answer lives in a later step, the flow jumps there."""
    if ADVANCE_WORDS.match(question) and index + 1 < len(steps):
        return {**narrate(version, case, steps, index + 1), "goto": index + 1}

    key = ("ask", version, case["id"], index, question.strip().lower())
    with _lock:
        if key in _cache:
            return {**_cache[key], "cached": True}

    shown = "\n\n".join(_step_payload(case, s, i, len(steps)) for i, s in enumerate(steps[: index + 1]))
    later = "\n\n".join(_step_payload(case, s, i, len(steps)) for i, s in enumerate(steps) if i > index) or "none"
    instructions = (
        'The analyst asked a question. Reply as JSON: {"reply": string, "answered_from_step": integer}.\n'
        "- Use whichever step's findings answer the question, including steps not yet shown.\n"
        "- answered_from_step is the step number (1-based) whose findings you mainly used.\n"
        "- If nothing in the findings answers it, say so honestly and use the current step number.\n"
        "- Reply under 90 words, same rules as before."
    )
    convo = [{"role": m["role"], "content": m["content"][:600]} for m in history[-4:] if m.get("role") in ("user", "assistant")]
    try:
        out = _call_groq(
            [{"role": "system", "content": SYSTEM_PROMPT},
             {"role": "user", "content": f"Steps already shown to the analyst:\n{shown}\n\nLater steps (already computed, not yet shown):\n{later}"},
             *convo,
             {"role": "user", "content": f"{instructions}\n\nCurrent step: {index + 1}\nAnalyst: {question}"}],
            json_mode=True,
        )
        parsed = json.loads(out["content"])
        used = int(parsed.get("answered_from_step", index + 1)) - 1
        goto = used if index < used < len(steps) else index
        result = {"reply": str(parsed.get("reply", "")).strip(), "goto": goto, "source": "live", "model": out["model"]}
        with _lock:
            _cache[key] = result
        return {**result, "cached": False}
    except (AgentUnavailable, json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
        return {"reply": "I can't reach the language model right now. Here's what the engine computed for this step:\n\n"
                         + offline_narration(steps[index]),
                "goto": index, "source": "offline", "model": None, "error": str(exc), "cached": False}


def draft_notice(version: int, case: Dict, outputs: Dict, index: int) -> Dict:
    """Write the notice for one action (e.g. to an affected financier) from the computed case outputs."""
    action = outputs["actions"][index]
    key = ("notice", version, case["id"], index)
    with _lock:
        if key in _cache:
            return {**_cache[key], "cached": True}
    facts = {"case": {k: case[k] for k in ("name", "location", "business", "risk_score", "headline")},
             "recipient": action["owner"], "requested_action": action["action"], "evidence": action["evidence"],
             "deadline": action["when"], "money_at_risk": outputs["money_at_risk"], "evidence_pack": outputs["evidence_pack"]}
    try:
        out = _call_groq([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "Write a short notice from Zeyro Trade Sentinel's fraud desk to the recipient below. "
                                        "Plain text, under 110 words: a one-line subject starting 'Subject:', then what we found, "
                                        "what we ask them to do and by when, and the key evidence as 2-3 short lines starting with '- '. "
                                        "Use only these facts, no invented names or numbers, and no signature block.\n\n"
                                        + json.dumps(facts, indent=1)},
        ])
        result = {"reply": out["content"], "source": "live", "model": out["model"]}
        with _lock:
            _cache[key] = result
    except AgentUnavailable as exc:
        result = {"reply": f"Subject: {case['name']}: {action['action']}\n\nTo {action['owner']}: {action['action']} ({action['when']}).\n"
                           f"- Why: {action['evidence']}\n- Money at risk: {outputs['money_at_risk']['amount']}",
                  "source": "offline", "model": None, "error": str(exc)}
    return {**result, "cached": False}


def clear_cache():
    with _lock:
        _cache.clear()


def prewarm(get_jobs, spacing: float = 7.0):
    """Narrate demo cases ahead of time, slowly, so the live demo never waits on rate limits."""
    def run():
        for version, case, steps in get_jobs():
            for i in range(len(steps)):
                if ("narrate", version, case["id"], i) in _cache:
                    continue
                narrate(version, case, steps, i)
                time.sleep(spacing)
    threading.Thread(target=run, daemon=True).start()
