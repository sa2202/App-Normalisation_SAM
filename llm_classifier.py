"""
llm_classifier.py
Optional LLM tier for UNRESOLVED rows. Uses Groq free API.
Sends only the top-N most relevant library entries per batch
to stay under the 8K TPM free-tier limit.
"""
import os, json, re
from difflib import SequenceMatcher

DEFAULT_MODEL = "openai/gpt-oss-20b"
BATCH_SIZE    = 3
TOP_N_ENTRIES = 30   # only send the N closest library entries, not all 345


def _get_client(api_key=None):
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError("Run: pip install openai")
    key = api_key or os.environ.get("GROQ_API_KEY")
    if not key:
        raise RuntimeError("No Groq API key. Get one free at https://console.groq.com")
    return OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")


def _top_entries(raw_names: list, library_rows, n: int):
    """Return the N library entries most similar to the batch of names."""
    query = " ".join(str(x).lower() for x in raw_names)
    scored = []
    for r in library_rows.itertuples():
        if str(r.publisher).startswith("("):
            continue
        candidate = f"{r.publisher} {r.product_family}".lower()
        score = SequenceMatcher(None, query, candidate).ratio()
        scored.append((score, r))
    scored.sort(key=lambda x: -x[0])
    return [r for _, r in scored[:n]]


def _build_prompt(raw_names: list, top_entries: list) -> str:
    lib = "\n".join(f"{r.canonical_id}: {r.publisher} {r.product_family}"
                    for r in top_entries)
    items = "\n".join(f"{i+1}. {n}" for i, n in enumerate(raw_names))
    return (
        f"Match these software names to the closest library entry.\n"
        f"Return null if unsure. Reply ONLY with JSON array.\n\n"
        f"LIBRARY:\n{lib}\n\n"
        f"NAMES:\n{items}\n\n"
        f'[{{"item":1,"canonical_id":"ID_OR_NULL","confidence":"high/low","reasoning":"brief"}}]'
    )


def _parse(text: str):
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if not m:
        raise ValueError(f"No JSON array: {text[:200]}")
    return json.loads(m.group(0))


def classify_unresolved_batch(raw_names: list, library_rows,
                               api_key=None, model=DEFAULT_MODEL,
                               batch_size=BATCH_SIZE) -> dict:
    if not raw_names:
        return {}
    client  = _get_client(api_key)
    results = {}

    for start in range(0, len(raw_names), batch_size):
        batch   = raw_names[start:start + batch_size]
        entries = _top_entries(batch, library_rows, TOP_N_ENTRIES)
        prompt  = _build_prompt(batch, entries)
        try:
            resp   = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=300,
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
