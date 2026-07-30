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

"""Optional OpenTelemetry tracing for the MCP tool surface.

Tracing is an opt-in feature gated behind the ``[otel]`` packaging extra. The
module imports OpenTelemetry lazily so that:

* importing this module never pulls in OpenTelemetry;
* :func:`init_tracing` degrades gracefully (returns ``False``) when the extra
  is not installed, rather than raising;
* :func:`trace_span` and :func:`traced_tool` are true zero-overhead no-ops
  until tracing has been initialised.

Enable it by installing the extra and either calling :func:`init_tracing`
directly or passing ``--otel-endpoint`` to the console entry point. When an
endpoint (or the standard ``OTEL_EXPORTER_OTLP_ENDPOINT`` environment
variable) is present, spans are exported over OTLP/HTTP via a batching
processor; otherwise a provider is still created so in-process exporters (for
example, tests) can attach their own span processors.
"""

from __future__ import annotations

import functools
import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, TypeVar, cast

if TYPE_CHECKING:  # pragma: no cover - typing-only imports
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.trace import Tracer

#: Default OpenTelemetry ``service.name`` resource attribute.
DEFAULT_SERVICE_NAME = "iso20022-bank-profile-mcp"

#: Standard OTLP endpoint environment variable honoured when no explicit
#: endpoint is passed to :func:`init_tracing`.
OTLP_ENDPOINT_ENV = "OTEL_EXPORTER_OTLP_ENDPOINT"

# Module state. ``None`` means tracing is not initialised, which selects the
# zero-overhead no-op path in :func:`trace_span` / :func:`traced_tool`.
_tracer: Tracer | None = None
_provider: TracerProvider | None = None

F = TypeVar("F", bound=Callable[..., Any])


def init_tracing(
    endpoint: str | None = None,
    service_name: str = DEFAULT_SERVICE_NAME,
) -> bool:
    """Initialise OpenTelemetry tracing for the server.

    Sets up a :class:`~opentelemetry.sdk.trace.TracerProvider` carrying a
    ``service.name`` resource. When ``endpoint`` (or the
    ``OTEL_EXPORTER_OTLP_ENDPOINT`` environment variable) resolves to a
    non-empty value, an OTLP/HTTP :class:`BatchSpanProcessor` is attached so
    spans are exported to a collector.

    Args:
        endpoint: OTLP/HTTP traces endpoint (for example
            ``http://localhost:4318/v1/traces``). Falls back to
            ``OTEL_EXPORTER_OTLP_ENDPOINT`` when omitted.
        service_name: Value of the ``service.name`` resource attribute.

    Returns:
        ``True`` when tracing was initialised; ``False`` when the optional
        ``[otel]`` extra is not installed (a graceful, non-fatal no-op).
    """
    global _tracer, _provider
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        return False

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    endpoint = endpoint or os.environ.get(OTLP_ENDPOINT_ENV)
    if endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )

        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
        )

    trace.set_tracer_provider(provider)
    # Bind the tracer to the provider we created rather than the process
    # global, so a repeat initialisation (for example in tests, where the
    # global provider is set-once) still yields a working tracer.
    _provider = provider
    _tracer = provider.get_tracer(service_name)
    return True


@contextmanager
def trace_span(name: str) -> Iterator[Any]:
    """Open a span named ``name`` for the duration of the ``with`` block.

    Records any exception raised inside the block on the span, marks the span
    status accordingly, and re-raises. A zero-overhead no-op (yielding
    ``None``) when tracing has not been initialised.

    Args:
        name: The span name.

    Yields:
        The active span, or ``None`` when tracing is inactive.
    """
    if _tracer is None:
        yield None
        return

    from opentelemetry.trace import Status, StatusCode

    # Own exception recording and status explicitly rather than letting the
    # span context manager double-record on the way out.
    with _tracer.start_as_current_span(
        name,
        record_exception=False,
        set_status_on_exception=False,
    ) as span:
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise
        else:
            span.set_status(Status(StatusCode.OK))


def traced_tool(name: str) -> Callable[[F], F]:
    """Decorate a tool function so each call runs inside a :func:`trace_span`.

    The wrapper is a zero-overhead no-op while tracing is inactive: it calls
    through to the wrapped function with a single ``None`` check and no span
    machinery. Outputs are never modified.

    Args:
        name: The span name to open per call.

    Returns:
        A decorator preserving the wrapped function's signature.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if _tracer is None:
                return func(*args, **kwargs)
            with trace_span(name):
                return func(*args, **kwargs)

        return cast(F, wrapper)

    return decorator
