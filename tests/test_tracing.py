# Copyright (C) 2023-2026 Sebastien Rousseau.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests for the optional OpenTelemetry tracing layer.

Exercises the real OpenTelemetry SDK through an in-memory span exporter (so no
collector is required) and the graceful degradation path when the optional
``[otel]`` extra is not installed.
"""

from __future__ import annotations

import builtins
from typing import Any

import pytest
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from opentelemetry.trace import StatusCode

from iso20022_bank_profile_mcp import tracing


@pytest.fixture(autouse=True)
def _reset_tracing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset module tracing state and clear the OTLP env before each test."""
    monkeypatch.delenv(tracing.OTLP_ENDPOINT_ENV, raising=False)
    monkeypatch.setattr(tracing, "_tracer", None)
    monkeypatch.setattr(tracing, "_provider", None)


def _install_memory_exporter() -> InMemorySpanExporter:
    """Attach an in-memory exporter to the initialised provider."""
    exporter = InMemorySpanExporter()
    assert tracing.provider() is not None
    tracing.provider().add_span_processor(SimpleSpanProcessor(exporter))
    return exporter


def test_init_tracing_returns_true_without_endpoint() -> None:
    """A bare ``init_tracing`` sets up a provider and tracer, no exporter."""
    assert tracing.init_tracing() is True
    assert tracing._tracer is not None
    assert tracing._provider is not None


def test_traced_tool_records_span_name() -> None:
    """``traced_tool`` opens a span named after the tool and marks it OK."""
    assert tracing.init_tracing(service_name="test-svc") is True
    exporter = _install_memory_exporter()

    @tracing.traced_tool("list_profiles")
    def op() -> str:
        return "ok"

    assert op() == "ok"

    spans: tuple[ReadableSpan, ...] = exporter.get_finished_spans()
    assert [s.name for s in spans] == ["list_profiles"]
    assert spans[0].status.status_code is StatusCode.OK


def test_trace_span_records_exception_and_status() -> None:
    """An exception inside a span is recorded and the status set to ERROR."""
    assert tracing.init_tracing() is True
    exporter = _install_memory_exporter()

    # try/except (not pytest.raises) so the post-block assertions are plainly
    # reachable to static analysis while still proving the exception re-raises.
    raised: ValueError | None = None
    try:
        with tracing.trace_span("failing_op"):
            raise ValueError("boom")
    except ValueError as exc:
        raised = exc
    assert raised is not None and str(raised) == "boom"

    (span,) = exporter.get_finished_spans()
    assert span.name == "failing_op"
    assert span.status.status_code is StatusCode.ERROR
    assert [event.name for event in span.events] == ["exception"]


def test_traced_tool_propagates_and_records_exception() -> None:
    """A raising tool re-raises while its span records the exception."""
    assert tracing.init_tracing() is True
    exporter = _install_memory_exporter()

    @tracing.traced_tool("boom_tool")
    def op() -> None:
        raise RuntimeError("kaboom")

    raised: RuntimeError | None = None
    try:
        op()
    except RuntimeError as exc:
        raised = exc
    assert raised is not None and str(raised) == "kaboom"

    (span,) = exporter.get_finished_spans()
    assert span.name == "boom_tool"
    assert span.status.status_code is StatusCode.ERROR


def test_init_tracing_with_endpoint_attaches_otlp_exporter() -> None:
    """Passing an endpoint wires an OTLP batch exporter without connecting."""
    assert (
        tracing.init_tracing(endpoint="http://localhost:4318/v1/traces")
        is True
    )
    assert tracing._provider is not None
    # Shut the batch processor's background worker down cleanly.
    tracing._provider.shutdown()


def test_init_tracing_honours_endpoint_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``OTEL_EXPORTER_OTLP_ENDPOINT`` is used when no endpoint is passed."""
    monkeypatch.setenv(
        tracing.OTLP_ENDPOINT_ENV, "http://localhost:4318/v1/traces"
    )
    assert tracing.init_tracing() is True
    assert tracing._provider is not None
    tracing._provider.shutdown()


def test_init_tracing_returns_false_when_extra_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing ``[otel]`` extra -> ``init_tracing`` returns ``False``."""
    real_import = builtins.__import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name.startswith("opentelemetry"):
            raise ImportError(f"no module named {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert tracing.init_tracing() is False
    assert tracing._tracer is None


def test_decorator_is_noop_when_uninitialised() -> None:
    """Without initialisation the decorator calls through with no spans."""
    calls: list[int] = []

    @tracing.traced_tool("noop")
    def op(value: int) -> int:
        calls.append(value)
        return value * 2

    assert tracing._tracer is None
    assert op(21) == 42
    assert calls == [21]


def test_trace_span_is_noop_when_uninitialised() -> None:
    """``trace_span`` yields ``None`` and does nothing when inactive."""
    assert tracing._tracer is None
    with tracing.trace_span("inactive") as span:
        assert span is None
