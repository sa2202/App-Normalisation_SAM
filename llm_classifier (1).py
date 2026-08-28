"""
llm_classifier.py
Optional 4th cascade tier: for rows still UNRESOLVED after exact/expanded/fuzzy
matching, ask an LLM to suggest a canonical match with reasoning.

Design choices, on purpose:
  - Only runs on the UNRESOLVED tail, never on rows the deterministic cascade
    already resolved - the LLM is a fallback, not a replacement for the
    explainable matching that makes an ELP audit-defensible.
  - Batches many rows into ONE prompt (default 15/call) instead of one call
    per row - this is what makes it usable on a free tier's rate limits
    (e.g. Groq's ~30 requests/min) when a client file has 200+ unresolved rows.
  - Returns a NEW confidence tier, "LLM_SUGGESTED", never EXACT/HIGH/REVIEW -
    it always needs a human to confirm in the app before it teaches the
    canonical library, same as every other low-confidence match.
  - Fails soft: if no API key is configured, or a call errors out, rows just
    stay UNRESOLVED - the rest of the pipeline works fine without this tier.

Get a free key at https://console.groq.com (no card required at time of
writing). Set it as an environment variable:

    export GROQ_API_KEY="your-key-here"

or pass it directly to classify_unresolved_batch().
"""

import os
import json
import re

DEFAULT_MODEL = "openai/gpt-oss-20b"   # fastest model on Groq free tier as of Aug 2026 (Llama/GPT-OSS replacements)
BATCH_SIZE = 15


def _get_client(api_key: str = None):
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError(
            "The 'openai' package is required for the LLM tier (Groq uses an "
            "OpenAI-compatible API). Install it with: pip install openai"
        )
    key = api_key or os.environ.get("GROQ_API_KEY")
    if not key:
        raise RuntimeError(
            "No Groq API key found. Set the GROQ_API_KEY environment variable, "
            "or pass api_key= directly. Get a free key at https://console.groq.com"
        )
    return OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")


def _build_prompt(raw_names: list, library_rows) -> str:
    library_lines = [
        f"- {r.canonical_id}: {r.publisher} | {r.product_family} | {r.edition or ''} | {r.version or ''}"
        for r in library_rows.itertuples()
    ]
    library_block = "\n".join(library_lines)

    items_block = "\n".join(f"{i+1}. {name}" for i, name in enumerate(raw_names))

    return f"""You are helping classify messy software product names from a client's IT \
asset export against a canonical product library, for Software Asset Management \
purposes. This is DEPLOYMENT data (something installed in an environment), not \
purchase/entitlement data.

CANONICAL LIBRARY:
{library_block}

RAW PRODUCT NAMES TO CLASSIFY:
{items_block}

For EACH numbered item, decide if it plausibly matches one canonical_id from the \
library above. Be conservative - if you are not reasonably confident, say null \
rather than guessing. Do not invent a canonical_id that isn't in the list.

Respond with ONLY a JSON array, no other text, one object per numbered item, in \
the same order, in this exact shape:
[
  {{"item": 1, "canonical_id": "MS-SQL-STD-2019", "confidence": "high", "reasoning": "short reason"}},
  {{"item": 2, "canonical_id": null, "confidence": "low", "reasoning": "not in library / ambiguous"}}
]
"""


def _extract_json_array(text: str):
    """LLMs sometimes wrap JSON in prose or code fences despite instructions -
    pull out the array defensively rather than trusting raw output."""
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON array found in LLM response: {text[:200]}")
    return json.loads(match.group(0))


def classify_unresolved_batch(raw_names: list, library_rows, api_key: str = None,
                               model: str = DEFAULT_MODEL, batch_size: int = BATCH_SIZE):
    """
    raw_names: list of raw strings still UNRESOLVED after the deterministic cascade
    library_rows: the ProductNormalizer's .lib dataframe (for building the prompt context)

    Returns: dict mapping raw_name -> {"canonical_id": str|None, "confidence": str, "reasoning": str}
             Rows the LLM call fails on, or that come back malformed, are simply
             omitted from the result - caller should treat missing entries as
             "still unresolved" rather than erroring the whole batch out.
    """
    if not raw_names:
        return {}

    client = _get_client(api_key)
    results = {}

    for start in range(0, len(raw_names), batch_size):
        batch = raw_names[start:start + batch_size]
        prompt = _build_prompt(batch, library_rows)

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=2000,
            )
            parsed = _extract_json_array(response.choices[0].message.content)
        except Exception as e:
            # Fail soft per-batch: these rows just stay unresolved.
            for name in batch:
                results[name] = {
                    "canonical_id": None, "confidence": "error",
                    "reasoning": f"LLM call failed: {e}",
                }
            continue

        for entry, raw_name in zip(parsed, batch):
            results[raw_name] = {
                "canonical_id": entry.get("canonical_id"),
                "confidence": entry.get("confidence", "unknown"),
                "reasoning": entry.get("reasoning", ""),
            }

    return results
