"""The provider catalogue probe: must not leak, must not lie, must not be
provider-specific.

Model ids were guessed for months because nothing in a developer sandbox could
ask a vendor what it serves — the keys live in CI. The probe runs there. Three
properties matter more than its output:

* it never prints a key (rule 6);
* a failed probe reports failure rather than looking healthy, which is the
  pathology every NVIDIA fix in this repo has been unwinding;
* it names no provider and no model in its logic, so adding a provider stays a
  config entry (``config/llm/providers.yaml``, ADR-008 §2).
"""
from __future__ import annotations

import json
import sys
import urllib.error
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
GITHUB_SCRIPTS = REPO_ROOT / ".github/scripts"
SCRIPT = GITHUB_SCRIPTS / "probe_catalogues.py"
WORKFLOW = REPO_ROOT / ".github/workflows/catalogue-probe.yml"

SECRET = "sk-do-not-print-me-0123456789"


@pytest.fixture
def probe():
    sys.path.insert(0, str(GITHUB_SCRIPTS))
    import probe_catalogues as mod

    return mod


def _provider(**overrides) -> SimpleNamespace:
    base = {
        "id": "acme",
        "kind": "openai",
        "base_url": "https://api.acme.test/v1",
        "key_env": ["ACME_API_KEY"],
        "default_model": "acme/model-1",
        "tier": "free",
        "priority": 10,
        "auth_style": "bearer",
        "extra_headers": {},
        "requires_key": True,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class TestItIsNotBuiltForOneVendor:
    """The bug being fixed is single-provider hardcoding; the fix must not
    reintroduce it in the diagnostic."""

    def test_no_model_id_appears_in_the_script(self) -> None:
        """The probe asks what exists; it must not tell.

        Checked against the real catalogue rather than a hand-written list of
        substrings — a substring check here matched the adapter kind "ollama"
        for containing "llama", which is the same false-confidence this whole
        line of work has been removing.
        """
        source = SCRIPT.read_text(encoding="utf-8")
        code = "\n".join(
            line for line in source.splitlines() if not line.strip().startswith("#")
        )
        body = code.split('"""', 2)[-1]  # drop the module docstring

        catalogue = yaml.safe_load(
            (REPO_ROOT / "config/llm/models.yaml").read_text(encoding="utf-8")
        )
        known = list((catalogue.get("models") or {}))
        assert known, "the catalogue is empty; this guard would pass vacuously"
        offenders = [model_id for model_id in known if model_id in body]
        assert not offenders, f"probe hardcodes catalogue models: {offenders}"

    def test_provider_ids_are_not_hardcoded_in_the_logic(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        body = source.split('"""', 2)[-1]
        for vendor in ("nvidia", "cerebras", "groq", "openrouter"):
            assert vendor not in body.lower(), (
                f"{vendor!r} is named in the probe's logic; providers come from config"
            )

    def test_every_adapter_kind_has_a_list_route(self, probe) -> None:
        """Whatever kinds the config can express, the probe must handle."""
        from packages.llm.config import load_config

        providers = list(load_config().providers.values())
        assert providers, "no providers configured; this guard would pass vacuously"
        # Resolved kinds, not raw ones: providers.yaml says `kind: lmstudio`
        # and `kind: vllm`, which are aliases for the OpenAI adapter. Checking
        # the raw value caught four providers the probe could not have read.
        missing = {probe._kind(p) for p in providers} - set(probe._LIST_MODELS)
        assert not missing, f"no list-models route for adapter kinds: {missing}"

    def test_it_walks_every_configured_provider(self, probe) -> None:
        ids = [p.id for p in probe._providers(None)]
        assert len(ids) > 1, "the probe must consider more than one provider"


class TestNoKeyEverReachesTheLog:
    """Rule 6: secrets are never logged, not even partially."""

    def test_a_full_run_never_emits_the_key(self, probe, monkeypatch, capsys) -> None:
        monkeypatch.setenv("ACME_API_KEY", SECRET)
        monkeypatch.setattr(probe, "_providers", lambda only: [_provider()])
        monkeypatch.setattr(
            probe, "_request", lambda p, path, key, payload=None: {"data": [{"id": "m"}]}
        )
        probe.main([])
        out = capsys.readouterr().out
        assert SECRET not in out
        assert SECRET[:10] not in out
        assert "key present: yes" in out

    def test_a_failing_request_never_emits_the_key(self, probe, monkeypatch, capsys) -> None:
        """Error paths print exception text — that must not carry the key."""
        monkeypatch.setenv("ACME_API_KEY", SECRET)
        monkeypatch.setattr(probe, "_providers", lambda only: [_provider()])

        def _boom(p, path, key, payload=None):
            raise OSError("connection refused")

        monkeypatch.setattr(probe, "_request", _boom)
        probe.main([])
        assert SECRET not in capsys.readouterr().out


class TestAFailedProbeIsNotASuccess:
    def test_no_reachable_provider_is_a_non_zero_exit(self, probe, monkeypatch) -> None:
        monkeypatch.delenv("ACME_API_KEY", raising=False)
        monkeypatch.setattr(probe, "_providers", lambda only: [_provider()])
        assert probe.main([]) == 1

    def test_an_unreachable_provider_is_a_non_zero_exit(self, probe, monkeypatch) -> None:
        monkeypatch.setenv("ACME_API_KEY", SECRET)
        monkeypatch.setattr(probe, "_providers", lambda only: [_provider()])

        def _boom(p, path, key, payload=None):
            raise OSError("no route to host")

        monkeypatch.setattr(probe, "_request", _boom)
        assert probe.main([]) == 1

    def test_a_listed_but_unservable_model_is_a_non_zero_exit(
        self, probe, monkeypatch
    ) -> None:
        """Listing is not proof. A retired id can still appear in a catalogue."""
        monkeypatch.setenv("ACME_API_KEY", SECRET)
        monkeypatch.setattr(probe, "_providers", lambda only: [_provider()])

        def _request(p, path, key, payload=None):
            if payload is None:
                return {"data": [{"id": "acme/model-1"}]}
            raise OSError("410 Gone")

        monkeypatch.setattr(probe, "_request", _request)
        assert probe.main(["--chat", "acme"]) == 1

    def test_a_healthy_provider_passes(self, probe, monkeypatch) -> None:
        monkeypatch.setenv("ACME_API_KEY", SECRET)
        monkeypatch.setattr(probe, "_providers", lambda only: [_provider()])

        def _request(p, path, key, payload=None):
            if payload is None:
                return {"data": [{"id": "acme/model-1"}]}
            return {"choices": [{"message": {"content": "ok"}}]}

        monkeypatch.setattr(probe, "_request", _request)
        assert probe.main(["--chat", "acme"]) == 0


class TestDisabledProvidersAreNotFalselyReportedUnreachable:
    """Local providers (ollama, lmstudio, vllm, localai) default to a
    localhost ``base_url`` and ``requires_key: false`` even when their
    ``*_ENABLED`` switch is off — so they passed both existing skip checks,
    got dialled anyway, and always failed in CI (nothing listens on
    localhost there). That produced permanent, unfixable "unreachable"
    noise in the scheduled drift issue (#1434) for providers nobody asked
    the probe to check.
    """

    def test_a_disabled_provider_is_skipped_in_a_full_sweep(
        self, probe, monkeypatch, capsys
    ) -> None:
        monkeypatch.setattr(
            probe, "_providers", lambda only: [_provider(enabled=False, requires_key=False)]
        )

        def _boom(p, path, key, payload=None):
            raise OSError("connection refused")

        monkeypatch.setattr(probe, "_request", _boom)
        probe.main([])
        out = capsys.readouterr().out

        assert "skipped — disabled here" in out
        assert "unreachable: acme" not in out

    def test_an_explicit_provider_request_still_probes_a_disabled_one(
        self, probe, monkeypatch, capsys
    ) -> None:
        """``gh workflow run ... -f provider=ollama`` must still work: an
        operator checking a candidate before flipping the switch on needs a
        real answer, not a silent skip."""
        monkeypatch.setattr(
            probe, "_providers", lambda only: [_provider(enabled=False, requires_key=False)]
        )

        def _boom(p, path, key, payload=None):
            raise OSError("connection refused")

        monkeypatch.setattr(probe, "_request", _boom)
        code = probe.main(["--provider", "acme"])
        out = capsys.readouterr().out

        assert "skipped — disabled here" not in out
        assert "unreachable: acme" in out
        assert code == 1

    def test_an_enabled_provider_is_unaffected(self, probe, monkeypatch, capsys) -> None:
        monkeypatch.setenv("ACME_API_KEY", SECRET)
        monkeypatch.setattr(probe, "_providers", lambda only: [_provider(enabled=True)])

        def _request(p, path, key, payload=None):
            return {"data": [{"id": "acme/model-1"}]}

        monkeypatch.setattr(probe, "_request", _request)
        probe.main([])
        out = capsys.readouterr().out

        assert "skipped — disabled here" not in out


class TestAuthFollowsTheProviderDeclaration:
    def test_bearer_is_the_default(self, probe) -> None:
        assert probe._auth_headers(_provider(), "k") == {"Authorization": "Bearer k"}

    def test_x_api_key_style(self, probe) -> None:
        headers = probe._auth_headers(_provider(auth_style="x-api-key"), "k")
        assert headers["x-api-key"] == "k"
        assert "anthropic-version" in headers

    def test_query_style_sends_no_auth_header(self, probe) -> None:
        assert probe._auth_headers(_provider(auth_style="query"), "k") == {}

    def test_no_key_sends_no_auth_header(self, probe) -> None:
        assert probe._auth_headers(_provider(), "") == {}


class TestTheWorkflowIsSafeAndReadOnly:
    @pytest.fixture
    def workflow(self) -> dict:
        return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))

    def test_inputs_are_not_interpolated_into_the_shell(self) -> None:
        """A ${{ }} expansion inside `run:` is pasted in as shell source, so a
        crafted input would execute as a command."""
        text = WORKFLOW.read_text(encoding="utf-8")
        for block in text.split("run: |")[1:]:
            assert "${{" not in block, "workflow inputs must reach run: via env"

    def test_it_reads_providers_and_writes_only_issues(self, workflow: dict) -> None:
        # The scheduled run opens/updates one drift-tracking issue; nothing here
        # writes repo contents. issues: write is the only write scope granted.
        assert workflow["permissions"] == {"contents": "read", "issues": "write"}

    def test_it_runs_on_schedule_and_dispatch(self, workflow: dict) -> None:
        # `on` parses as True under YAML 1.1 unless quoted; accept either key.
        triggers = workflow.get("on", workflow.get(True))
        assert set(triggers) == {"workflow_dispatch", "schedule"}, (
            "the probe now runs on a cadence (catalogued in loops/registry.yaml)"
        )
        crons = [c["cron"] for c in triggers["schedule"]]
        assert crons, "the schedule trigger must declare a cron expression"

    def test_only_the_scheduled_run_files_an_issue(self) -> None:
        # A manual dispatch stays side-effect-free: the issue-filing step is
        # gated to the scheduled event.
        text = WORKFLOW.read_text(encoding="utf-8")
        assert "probe_report.py" in text, "the drift-report step must be wired"
        assert "github.event_name == 'schedule'" in text, (
            "issue-filing must be gated to the scheduled event"
        )

    def test_it_does_not_commit_or_push(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        for forbidden in ("git commit", "git push", "create_pull_request", "gh pr"):
            assert forbidden not in text


class TestTheWorkflowInstallsWhatTheImportNeeds:
    """The first real run died in 10 seconds on ModuleNotFoundError: httpx.

    The probe itself only uses ``urllib``, so installing ``pyyaml`` looked
    sufficient. It is not: ``_providers`` imports ``packages.llm.config``, and
    ``packages/llm/__init__`` imports the router, which imports ``httpx``. The
    dependency is real but invisible at the call site — exactly the kind of
    thing that is cheap to assert and expensive to rediscover.
    """

    def test_the_install_step_covers_the_transitive_imports(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        install = [line for line in text.splitlines() if "pip install" in line]
        assert install, "the workflow must install the config dependencies"
        joined = " ".join(install)
        for package in ("pyyaml", "httpx"):
            assert package in joined, f"{package} is needed to load the provider config"


class TestAListingFailureDoesNotVetoTheAnswer:
    """A refused catalogue says nothing about whether a named model answers.

    On 2026-08-29 a probe run with ``--chat cerebras --model <candidate>``
    printed ``list-models failed: HTTP 403 — Forbidden`` and stopped there. The
    provider loop appended the id to ``unreachable`` and moved on, so the
    completion it had been explicitly asked to send was never sent, and the
    question the run existed to answer — does this candidate serve? — came back
    blank.

    That is the script contradicting its own thesis. Listing is not proof;
    answering is. A listing that cannot be read must therefore not be able to
    veto the answering.
    """

    @staticmethod
    def _cannot_list(answers: bool = True):
        """A provider whose /models refuses but whose /chat works."""

        def _request(p, path, key, payload=None):
            if payload is None:
                raise OSError("403 Forbidden")
            if not answers:
                raise OSError("404 Not Found")
            return {"choices": [{"message": {"content": "ok"}}]}

        return _request

    def test_an_explicit_model_is_still_called(self, probe, monkeypatch, capsys) -> None:
        monkeypatch.setenv("ACME_API_KEY", SECRET)
        monkeypatch.setattr(probe, "_providers", lambda only: [_provider()])
        monkeypatch.setattr(probe, "_request", self._cannot_list())

        code = probe.main(["--chat", "acme", "--model", "acme/candidate-9"])
        out = capsys.readouterr().out

        assert "list-models failed" in out, "the listing failure must still be reported"
        assert "acme/candidate-9: HTTP 200" in out, (
            "the named model was never called; the listing failure vetoed it"
        )
        assert code == 0, "the provider answered a completion, so it is reachable"

    def test_the_default_model_is_still_called(self, probe, monkeypatch, capsys) -> None:
        """No ``--model`` given: the provider's declared default is the target."""
        monkeypatch.setenv("ACME_API_KEY", SECRET)
        monkeypatch.setattr(probe, "_providers", lambda only: [_provider()])
        monkeypatch.setattr(probe, "_request", self._cannot_list())

        probe.main(["--chat", "acme"])
        assert "acme/model-1: HTTP 200" in capsys.readouterr().out

    def test_it_is_reported_apart_from_unreachable(self, probe, monkeypatch, capsys) -> None:
        """Answered-but-unlistable is a different fact from unreachable.

        Collapsing the two is how a working provider gets written off, which is
        the mistake that retired a model in this repo on 2026-08-28.
        """
        monkeypatch.setenv("ACME_API_KEY", SECRET)
        monkeypatch.setattr(probe, "_providers", lambda only: [_provider()])
        monkeypatch.setattr(probe, "_request", self._cannot_list())

        probe.main(["--chat", "acme", "--model", "acme/candidate-9"])
        out = capsys.readouterr().out

        assert "reachable providers: 1" in out
        assert "unreachable: acme" not in out
        assert "answered but would not list: acme" in out

    def test_a_model_that_will_not_answer_still_fails(self, probe, monkeypatch, capsys) -> None:
        """The relaxation must not turn a real failure into a pass."""
        monkeypatch.setenv("ACME_API_KEY", SECRET)
        monkeypatch.setattr(probe, "_providers", lambda only: [_provider()])
        monkeypatch.setattr(probe, "_request", self._cannot_list(answers=False))

        code = probe.main(["--chat", "acme", "--model", "acme/candidate-9"])
        out = capsys.readouterr().out

        assert code == 1
        assert "acme/candidate-9" in out
        assert "reachable providers: 0" in out

    def test_without_chat_a_listing_failure_is_still_unreachable(
        self, probe, monkeypatch, capsys
    ) -> None:
        """Nothing was asked to be called, so nothing proved the provider is up."""
        monkeypatch.setenv("ACME_API_KEY", SECRET)
        monkeypatch.setattr(probe, "_providers", lambda only: [_provider()])
        monkeypatch.setattr(probe, "_request", self._cannot_list())

        assert probe.main([]) == 1
        assert "unreachable: acme" in capsys.readouterr().out

    def test_the_key_stays_out_of_this_path_too(self, probe, monkeypatch, capsys) -> None:
        """Rule 6, re-asserted on the branch this change introduces."""
        monkeypatch.setenv("ACME_API_KEY", SECRET)
        monkeypatch.setattr(probe, "_providers", lambda only: [_provider()])
        monkeypatch.setattr(probe, "_request", self._cannot_list())

        probe.main(["--chat", "acme", "--model", "acme/candidate-9", "--tools"])
        out = capsys.readouterr().out
        assert SECRET not in out
        assert SECRET[:10] not in out

    def test_a_kind_with_no_chat_route_is_not_counted_as_an_answer(
        self, probe, monkeypatch, capsys
    ) -> None:
        """A call that was never sent is not evidence that anything answered.

        ``_LIST_MODELS`` knows four adapter kinds; ``_CHAT`` knows two. For the
        other two, ``--chat`` has nothing to send. Before the reachability rule
        changed that was harmless — the provider had already been counted
        reachable by its listing. It is not harmless now: a skipped call that
        reads as an answer would make an unreachable provider exit zero.
        """
        monkeypatch.setenv("ACME_API_KEY", SECRET)
        monkeypatch.setattr(probe, "_providers", lambda only: [_provider(kind="gemini")])
        monkeypatch.setattr(probe, "_request", self._cannot_list())
        assert "gemini" in probe._LIST_MODELS and "gemini" not in probe._CHAT

        code = probe.main(["--chat", "acme"])
        out = capsys.readouterr().out

        assert "no chat route known" in out
        assert code == 1, "nothing was actually called, so nothing was proved"
        assert "unreachable: acme" in out


class TestTheProbeIdentifiesItself:
    """``urllib``'s default User-Agent is a 403 waiting to happen.

    Unset, every request goes out as ``Python-urllib/3.13``. Edge filters in
    front of several vendor APIs reject that outright — and the rejection is a
    403, which is indistinguishable by status alone from a revoked key. A probe
    whose entire job is to tell "it refused" apart from "it is not there" must
    not introduce a third possibility it cannot see.
    """

    def test_every_request_carries_a_real_user_agent(self, probe) -> None:
        sent = {}

        class _Resp:
            def read(self):
                return b"{}"

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        def _urlopen(req, timeout=None):
            sent.update(req.headers)
            return _Resp()

        import urllib.request

        original = urllib.request.urlopen
        urllib.request.urlopen = _urlopen
        try:
            probe._request(_provider(), "models", "k")
        finally:
            urllib.request.urlopen = original

        agent = sent.get("User-agent", "")
        assert agent, "no User-Agent sent; urllib would default to Python-urllib"
        assert "urllib" not in agent.lower()

    def test_a_provider_can_override_it(self, probe) -> None:
        """``extra_headers`` is applied last, so a provider stays in control."""
        source = SCRIPT.read_text(encoding="utf-8")
        agent_at = source.index('"User-Agent"')
        extra_at = source.index("provider.extra_headers")
        assert agent_at < extra_at, (
            "extra_headers must be merged after the default User-Agent"
        )


class TestTheJsonSummary:
    """`--json PATH` writes a machine-readable summary the scheduled drift-report
    step consumes. It must record per-failure status detail and never a key."""

    def test_a_healthy_run_writes_ok_true(self, probe, monkeypatch, tmp_path) -> None:
        monkeypatch.setenv("ACME_API_KEY", SECRET)
        monkeypatch.setattr(probe, "_providers", lambda only: [_provider()])

        def _request(p, path, key, payload=None):
            if payload is None:
                return {"data": [{"id": "acme/model-1"}]}
            return {"choices": [{"message": {"content": "ok"}}]}

        monkeypatch.setattr(probe, "_request", _request)
        out = tmp_path / "summary.json"
        assert probe.main(["--chat", "acme", "--json", str(out)]) == 0

        summary = json.loads(out.read_text(encoding="utf-8"))
        assert summary["ok"] is True
        assert summary["unservable"] == []
        assert summary["unservable_detail"] == []

    def test_a_dead_model_is_recorded_with_its_status_code(
        self, probe, monkeypatch, tmp_path
    ) -> None:
        monkeypatch.setenv("ACME_API_KEY", SECRET)
        monkeypatch.setattr(probe, "_providers", lambda only: [_provider()])

        def _request(p, path, key, payload=None):
            if payload is None:
                return {"data": [{"id": "acme/model-1"}]}
            raise urllib.error.HTTPError(
                "https://api.acme.test/v1/chat", 410, "Gone", {}, None
            )

        monkeypatch.setattr(probe, "_request", _request)
        out = tmp_path / "summary.json"
        assert probe.main(["--chat", "acme", "--json", str(out)]) == 1

        summary = json.loads(out.read_text(encoding="utf-8"))
        assert summary["ok"] is False
        assert summary["unservable"] == ["acme:acme/model-1"]
        assert summary["unservable_detail"] == [
            {"id": "acme:acme/model-1", "detail": "HTTP 410"}
        ]
        # The key never lands in the report.
        assert SECRET not in out.read_text(encoding="utf-8")
