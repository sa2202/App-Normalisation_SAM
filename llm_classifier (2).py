"""
llm_classifier.py
Optional LLM tier for rows still UNRESOLVED after the deterministic cascade.
Uses Groq's free API (openai/gpt-oss-20b as of Aug 2026).

Get a free key at https://console.groq.com (no card required).
Set GROQ_API_KEY env var or paste in the app UI.
"""

import os
import json
import re

DEFAULT_MODEL = "openai/gpt-oss-20b"
BATCH_SIZE    = 3   # small batches - free tier limit is 8K tokens/min


def _get_client(api_key=None):
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError("Run: pip install openai")
    key = api_key or os.environ.get("GROQ_API_KEY")
    if not key:
        raise RuntimeError("No Groq API key. Get one free at https://console.groq.com")
    return OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")


def _build_prompt(raw_names: list, library_rows) -> str:
    # Send only publisher + product family to keep prompt small enough for
    # the free-tier 8K token/min limit. Edition/version not needed for the
    # LLM to make a useful suggestion on genuinely unresolved rows.
    lib_lines = [
        f"{r.canonical_id}: {r.publisher} {r.product_family}"
        for r in library_rows.itertuples()
        if not str(r.publisher).startswith("(")  # skip Freeware/Component entries
    ]
    lib_block = "\n".join(lib_lines)
    items     = "\n".join(f"{i+1}. {n}" for i, n in enumerate(raw_names))

    return f"""Match these software names to the closest entry in the library.
Be conservative - return null if unsure. Reply ONLY with a JSON array.

LIBRARY (canonical_id: publisher product):
{lib_block}

NAMES TO MATCH:
{items}

JSON shape (one object per name, same order):
[{{"item":1,"canonical_id":"MS-SQL-STD-2019","confidence":"high","reasoning":"brief"}},
 {{"item":2,"canonical_id":null,"confidence":"low","reasoning":"not found"}}]"""


def _parse(text: str):
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if not m:
        raise ValueError(f"No JSON array in response: {text[:200]}")
    return json.loads(m.group(0))


def classify_unresolved_batch(raw_names: list, library_rows,
                               api_key=None, model=DEFAULT_MODEL,
                               batch_size=BATCH_SIZE) -> dict:
    if not raw_names:
        return {}

    client  = _get_client(api_key)
    results = {}

    for start in range(0, len(raw_names), batch_size):
        batch  = raw_names[start:start + batch_size]
        prompt = _build_prompt(batch, library_rows)
        try:
            resp   = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=500,
            )
            parsed = _parse(resp.choices[0].message.content)
        except Exception as e:
            for name in batch:
                results[name] = {"canonical_id": None, "confidence": "error",
                                 "reasoning": f"LLM call failed: {e}"}
            continue

        for entry, name in zip(parsed, batch):
            results[name] = {
                "canonical_id": entry.get("canonical_id"),
                "confidence":   entry.get("confidence", "unknown"),
                "reasoning":    entry.get("reasoning", ""),
            }

    return results
