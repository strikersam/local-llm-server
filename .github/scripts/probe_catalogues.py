#!/usr/bin/env python3
"""Ask every configured provider what it actually serves.

Model ids in this repo were guessed for months, and the guesses rotted: four
separate outages, each one a hand-edited id that a vendor had retired. The
guessing was not laziness — it was unavoidable. The keys live in CI and Render,
a developer sandbox has no route to the vendors, and so nobody could check.

This closes that loop for *all* providers, not one. It reads
``config/llm/providers.yaml`` (plus the environment-derived defaults in
``packages/llm/config.py``), and for every provider that has a key it asks that
provider's own list-models endpoint what exists. Adding a provider stays a
config entry: this script learns about it automatically.

It is read-only. It never writes to the repo, and it never prints a key —
only whether one is present.

Usage::

    python .github/scripts/probe_catalogues.py                    # every provider
    python .github/scripts/probe_catalogues.py --provider nvidia  # just one
    python .github/scripts/probe_catalogues.py --filter nemotron  # dump raw records
    python .github/scripts/probe_catalogues.py --chat nvidia      # prove it answers
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

TIMEOUT = 30.0
USER_AGENT = "autonomous-ai-agency-catalogue-probe/1.0 (+https://github.com/strikersam/autonomous-ai-agency)"

# How to list models, per adapter kind. This is adapter knowledge — the shape of
# each vendor's API — not a list of models. No model id appears in this file.
#
#   path      appended to the provider's base_url
#   records   key in the JSON response holding the list
#   ident     key on each record holding the model id
_LIST_MODELS = {
    "openai": {"path": "models", "records": "data", "ident": "id"},
    "anthropic": {"path": "v1/models", "records": "data", "ident": "id"},
    "gemini": {"path": "models", "records": "models", "ident": "name"},
    "ollama": {"path": "api/tags", "records": "models", "ident": "name"},
}

# How to send a minimal completion, per adapter kind. Used only by --chat.
_CHAT = {
    "openai": {"path": "chat/completions", "wraps_max_tokens": "max_tokens"},
    "anthropic": {"path": "v1/messages", "wraps_max_tokens": "max_tokens"},
}


def _kind(provider) -> str:
    """The adapter kind, through the platform's own alias table.

    ``providers.yaml`` may say ``kind: lmstudio`` or ``kind: vllm``; both are
    OpenAI-compatible. Re-deriving that mapping here would be a second source of
    truth for exactly the kind of thing this repo keeps getting wrong.
    """
    from packages.llm.providers import resolve_kind

    return resolve_kind(provider.kind)


def _resolve_key(provider) -> str:
    """First non-empty value among the provider's declared key env names."""
    for name in provider.key_env or []:
        value = (os.environ.get(name) or "").strip()
        if value:
            return value
    return ""


def _auth_headers(provider, key: str) -> dict[str, str]:
    """Auth per the provider's declared style. Never logged."""
    style = (provider.auth_style or "bearer").lower()
    if not key or style == "none":
        return {}
    if style == "x-api-key":
        return {"x-api-key": key, "anthropic-version": "2023-06-01"}
    if style == "query":
        return {}  # carried in the URL instead
    return {"Authorization": f"Bearer {key}"}


def _request(provider, path: str, key: str, payload: dict | None = None) -> dict:
    """One request to a provider. Raises on transport or HTTP error."""
    base = (provider.base_url or "").rstrip("/")
    url = f"{base}/{path.lstrip('/')}"
    if (provider.auth_style or "").lower() == "query" and key:
        url = f"{url}?{urllib.parse.urlencode({'key': key})}"

    data = json.dumps(payload).encode() if payload is not None else None
    headers = {
        "Accept": "application/json",
        # urllib's default identifies as "Python-urllib/x.y", which edge
        # filters in front of several vendor APIs reject outright — a 403 that
        # looks exactly like a bad key and is not one. A diagnostic should say
        # what it is anyway. Overridable per provider via extra_headers.
        "User-Agent": USER_AGENT,
        **_auth_headers(provider, key),
    }
    if data:
        headers["Content-Type"] = "application/json"
    headers.update(provider.extra_headers or {})

    req = urllib.request.Request(
        url, data=data, headers=headers, method="POST" if data else "GET"
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode())


def list_models(provider, key: str) -> list[dict]:
    """Raw records from the provider's list-models endpoint."""
    kind = _kind(provider)
    spec = _LIST_MODELS.get(kind)
    if spec is None:
        raise ValueError(f"no list-models route known for kind {kind!r}")
    body = _request(provider, spec["path"], key)
    records = body.get(spec["records"]) or []
    return [record for record in records if isinstance(record, dict)]


def probe_chat(provider, key: str, model_id: str) -> tuple[bool, str]:
    """Send the smallest possible completion.

    A model can be listed and still refuse to serve — that is exactly how the
    retired ids kept looking healthy. Listing is not proof; answering is.

    Only called for kinds this script knows how to call: a skipped call must
    never be able to return ``True``, because the caller reads ``True`` as
    evidence that the provider is up.

    Returns ``(ok, detail)``. ``detail`` is a short, secret-free status token
    (``"HTTP 200"``, ``"HTTP 410"``, or an exception class name) so a scheduled
    caller can report *which* status code a dead id answered with.
    """
    spec = _CHAT[_kind(provider)]
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": "Reply with the word: ok"}],
        spec["wraps_max_tokens"]: 8,
    }
    try:
        body = _request(provider, spec["path"], key, payload)
    except urllib.error.HTTPError as exc:
        print(f"    {model_id}: HTTP {exc.code} — {exc.reason}")
        return False, f"HTTP {exc.code}"
    except Exception as exc:  # noqa: BLE001 - diagnostic, report anything
        print(f"    {model_id}: {type(exc).__name__}: {exc}")
        return False, type(exc).__name__

    choices = body.get("choices") or body.get("content") or [{}]
    first = choices[0] if isinstance(choices, list) and choices else {}
    text = (first.get("message") or {}).get("content") or first.get("text") or ""
    print(f"    {model_id}: HTTP 200 — {str(text)[:80]!r}")
    return True, "HTTP 200"


_PROBE_TOOL = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get the current weather for a city.",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
        },
    },
}


def probe_tools(provider, key: str, model_id: str) -> bool:
    """Does this model actually emit a tool call?

    ``config/llm/models.yaml`` declares ``supports_tools`` per model, and
    ``packages/llm/registry.py`` filters tool-calling requests on it — giving
    anything undeclared ``supports_tools: false``. So an undeclared model is
    silently excluded from every tool-calling request. Declaring it needs
    evidence, and this is the evidence.
    """
    kind = _kind(provider)
    spec = _CHAT.get(kind)
    if spec is None:
        print(f"    (no chat route known for kind {kind!r}; tools not probed)")
        return False

    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": "What is the weather in Paris?"}],
        "tools": [_PROBE_TOOL],
        "tool_choice": "auto",
        spec["wraps_max_tokens"]: 128,
    }
    try:
        body = _request(provider, spec["path"], key, payload)
    except Exception as exc:  # noqa: BLE001 - diagnostic, report anything
        print(f"    tools {model_id}: {type(exc).__name__}: {exc}")
        return False

    choices = body.get("choices") or [{}]
    message = (choices[0] or {}).get("message") or {}
    calls = message.get("tool_calls") or []
    named = [((c.get("function") or {}).get("name")) for c in calls if isinstance(c, dict)]
    print(f"    tools {model_id}: {'YES' if named else 'no tool_calls'} {named or ''}")
    return bool(named)


def _providers(only: str | None):
    from packages.llm.config import load_config

    config = load_config()
    items = sorted(config.providers.values(), key=lambda p: (p.priority, p.id))
    if only:
        items = [p for p in items if p.id == only]
        if not items:
            known = ", ".join(sorted(config.providers))
            raise SystemExit(f"unknown provider {only!r}; configured: {known}")
    return items


@dataclass
class ProviderOutcome:
    """What one provider proved about itself in a single run."""

    listed: bool = False
    answered: bool = False
    unservable: list[str] = field(default_factory=list)
    # Per-failure detail for the scheduled report: {"id": "provider:model",
    # "detail": "HTTP 410"}. Kept apart from ``unservable`` so the printed
    # summary format never changes.
    unservable_detail: list[dict] = field(default_factory=list)

    @property
    def reachable(self) -> bool:
        """Either route proves the provider is there; answering is the stronger.

        A provider whose catalogue endpoint refuses but whose model returns a
        completion is reachable. Treating it as unreachable was this script
        contradicting its own thesis.
        """
        return self.listed or self.answered


def _chat_targets(provider, args, ids: list[str]) -> list[str]:
    """Which model ids ``--chat`` should call for this provider.

    Explicit ``--model`` ids are honoured even when the catalogue could not be
    read. A listing endpoint that refuses says nothing about whether a named
    model answers, and answering is the only evidence this script trusts.
    """
    if provider.id not in args.chat:
        return []
    targets = list(args.model) or [provider.default_model or (ids[0] if ids else "")]
    return [target for target in targets if target]


def _dump_matching(records: list[dict], ident: str, needle: str) -> None:
    """Raw records whose id contains ``needle`` — for reading vendor metadata."""
    if not needle:
        return
    matched = [r for r in records if needle.lower() in str(r.get(ident, "")).lower()]
    print(f"    raw records matching {needle!r}: {len(matched)}")
    for record in matched:
        print(json.dumps(record, indent=2, sort_keys=True))


def _list_or_report(provider, key: str) -> list[dict] | None:
    """Catalogue records, or ``None`` after printing why there are none."""
    try:
        return list_models(provider, key)
    except urllib.error.HTTPError as exc:
        print(f"    list-models failed: HTTP {exc.code} — {exc.reason}")
    except Exception as exc:  # noqa: BLE001 - diagnostic, report anything
        print(f"    list-models failed: {type(exc).__name__}: {exc}")
    return None


def probe_provider(provider, key: str, args) -> ProviderOutcome:
    """List what the provider claims, then call what it was asked to call.

    The two are independent on purpose. The earlier version returned early on a
    listing failure, so ``--chat`` and ``--model`` were silently discarded for
    exactly the providers whose catalogue is hardest to read.
    """
    outcome = ProviderOutcome()
    ids: list[str] = []

    records = _list_or_report(provider, key)
    if records is not None:
        outcome.listed = True
        ident = _LIST_MODELS[_kind(provider)]["ident"]
        ids = [str(r.get(ident) or "") for r in records if r.get(ident)]
        print(f"    models served: {len(ids)}")
        for model_id in ids:
            print(f"      - {model_id}")
        _dump_matching(records, ident, args.filter)

    targets = _chat_targets(provider, args, ids)
    if provider.id in args.chat and not targets:
        print("    --chat: no model to call")
    if targets and _kind(provider) not in _CHAT:
        # A call that was never sent is not an answer. Letting it count as one
        # would make a provider look reachable on no evidence — the failure
        # mode this whole script exists to remove.
        print(f"    (no chat route known for kind {_kind(provider)!r}; skipped)")
        targets = []
    for target in targets:
        ok, detail = probe_chat(provider, key, target)
        if not ok:
            outcome.unservable.append(f"{provider.id}:{target}")
            outcome.unservable_detail.append(
                {"id": f"{provider.id}:{target}", "detail": detail}
            )
            continue
        outcome.answered = True
        if args.tools:
            probe_tools(provider, key, target)
    return outcome


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", default=None, help="probe only this provider id")
    parser.add_argument(
        "--filter",
        default="",
        help="dump raw records whose id contains this substring",
    )
    parser.add_argument(
        "--chat",
        action="append",
        default=[],
        help="provider id whose default model should be called; repeatable",
    )
    parser.add_argument(
        "--tools",
        action="store_true",
        help="also send a tool-calling request, to establish supports_tools by evidence",
    )
    parser.add_argument(
        "--model",
        action="append",
        default=[],
        help=(
            "specific model id to call on the --chat provider; repeatable. "
            "A catalogue listing is not proof a model serves — this is how you "
            "check a candidate before making it a default. Called even when the "
            "catalogue itself cannot be read."
        ),
    )
    parser.add_argument(
        "--json",
        default="",
        metavar="PATH",
        help=(
            "also write a machine-readable summary of the run to PATH "
            "(reachable count + unreachable/unlistable/unservable ids with status "
            "detail). Used by the scheduled drift-report step; never prints a key."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    reachable = 0
    unreachable: list[str] = []
    unlistable: list[str] = []
    unservable: list[str] = []
    unservable_detail: list[dict] = []

    for provider in _providers(args.provider):
        key = _resolve_key(provider)
        # Presence only — never the value, never a prefix of it.
        state = "yes" if key else "no"
        print(f"\n=== {provider.id} ({_kind(provider)}, tier={provider.tier})")
        print(f"    base_url: {provider.base_url or '(unset)'}")
        print(f"    key present: {state}")

        if not getattr(provider, "enabled", True) and not args.provider:
            # Local providers (ollama, lmstudio, vllm, localai) default to a
            # localhost base_url even when disabled, so they pass the two
            # checks below and get dialled anyway — always failing in CI,
            # where nothing listens on that port. That is not drift; it is
            # the operator's own switch. An explicit `--provider <id>` still
            # probes it, for checking a candidate before flipping it on.
            print("    skipped — disabled here (pass --provider to probe anyway)")
            continue
        if provider.requires_key and not key:
            print("    skipped — no key configured here")
            continue
        if not provider.base_url:
            print("    skipped — no base_url configured")
            continue

        outcome = probe_provider(provider, key, args)
        unservable.extend(outcome.unservable)
        unservable_detail.extend(outcome.unservable_detail)
        if outcome.reachable:
            reachable += 1
        else:
            unreachable.append(provider.id)
        if outcome.answered and not outcome.listed:
            unlistable.append(provider.id)

    print(f"\nreachable providers: {reachable}")
    if unreachable:
        print(f"unreachable: {', '.join(unreachable)}")
    if unlistable:
        # Not the same failure as unreachable, and worth saying out loud: the
        # provider answered a completion, so any "models served" list above is
        # missing for it rather than empty.
        print(f"answered but would not list: {', '.join(unlistable)}")
    if unservable:
        print(f"named but would not answer: {', '.join(unservable)}")
    # A probe that cannot reach anything must not look like a healthy one.
    ok = not (unreachable or unservable or reachable == 0)

    if args.json:
        summary = {
            "ok": ok,
            "reachable": reachable,
            "unreachable": unreachable,
            "unlistable": unlistable,
            "unservable": unservable,
            "unservable_detail": unservable_detail,
        }
        # Best-effort: a diagnostic that cannot write its own report file must
        # not change the probe's own pass/fail verdict.
        try:
            with open(args.json, "w", encoding="utf-8") as fh:
                json.dump(summary, fh, indent=2, sort_keys=True)
        except OSError as exc:
            print(f"    (could not write --json {args.json!r}: {exc})")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
