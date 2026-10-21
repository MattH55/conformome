"""The download circuit breaker: a source whose host keeps timing out is skipped for the rest of the run."""
import urllib.error
from types import SimpleNamespace

from conformome import pipeline


def _module(name, behaviour):
    calls = []

    def fetch(paths, acc, retrieved):
        calls.append(acc)
        behaviour(acc)

    return SimpleNamespace(NAME=name, fetch=fetch, calls=calls)


def _timeout(acc):
    raise urllib.error.URLError(TimeoutError("[Errno 110] Connection timed out"))


def _http_404(acc):
    raise urllib.error.HTTPError("https://example.org", 404, "Not Found", {}, None)


def _ok(acc):
    return None


def _run(monkeypatch, tmp_path, modules, accessions):
    primary = _module("Primary", _ok)
    monkeypatch.setattr(pipeline, "sources_for", lambda mtype: [primary, *modules])
    monkeypatch.setattr(pipeline, "PRIMARY", {"protein": primary})
    monkeypatch.setattr(pipeline, "fetch_identity", lambda paths, acc, retrieved: None)
    monkeypatch.setattr(pipeline, "_representatives", lambda paths, accs: [])
    paths = SimpleNamespace(raw=tmp_path)
    pipeline.download(paths, accessions)
    return primary


def test_unreachable_source_is_skipped_after_two_timeouts(monkeypatch, tmp_path):
    slow = _module("Slow", _timeout)
    fine = _module("Fine", _ok)
    accs = ["P00001", "P00002", "P00003", "P00004"]
    primary = _run(monkeypatch, tmp_path, [slow, fine], accs)
    assert slow.calls == accs[:pipeline.UNREACHABLE_AFTER]
    assert fine.calls == accs and primary.calls == accs
    failures = pipeline.read_json(tmp_path / "download_failures.json")
    skipped = [f for f in failures if f["error"].startswith("skipped")]
    assert [f["molecule_id"] for f in skipped] == accs[pipeline.UNREACHABLE_AFTER:]


def test_http_errors_do_not_trip_the_breaker(monkeypatch, tmp_path):
    missing = _module("Missing", _http_404)
    accs = ["P00001", "P00002", "P00003"]
    _run(monkeypatch, tmp_path, [missing], accs)
    assert missing.calls == accs


def test_a_success_resets_the_count(monkeypatch, tmp_path):
    pattern = {"P00001": _timeout, "P00002": _ok, "P00003": _timeout, "P00004": _ok}
    flaky = _module("Flaky", lambda acc: pattern[acc](acc))
    accs = list(pattern)
    _run(monkeypatch, tmp_path, [flaky], accs)
    assert flaky.calls == accs
