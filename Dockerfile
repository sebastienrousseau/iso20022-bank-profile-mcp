# syntax=docker/dockerfile:1.6
# Multi-stage build for a minimal iso20022-bank-profile-mcp image.
#
# The container runs the FastMCP clearing-profile server over stdio so an MCP
# client can launch it directly with
# ``docker run -i --rm iso20022-bank-profile-mcp``.
#
# NOTE: this server is fully local and closed-world. It has NO sub-servers and
# opens NO network sockets: every tool (``list_profiles``, ``get_profile``,
# ``lint_payload``, ``validate_profile_definition``) computes from the bundled
# clearing-profile data, so no additional servers need to be present at
# runtime. (Sub-servers are not applicable to this image.)

FROM python:3.14-slim@sha256:cea0e6040540fb2b965b6e7fb5ffa00871e632eef63719f0ea54bca189ce14a6 AS builder

WORKDIR /build

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# pyproject.toml carries ``readme = "README.md"``, so README.md must be
# present at build-time for ``pip install .`` to resolve the package
# metadata. The bundled clearing-profile JSON ships inside the package tree.
COPY pyproject.toml README.md ./
COPY iso20022_bank_profile_mcp ./iso20022_bank_profile_mcp

# Install this package (and its published runtime deps: mcp, pydantic,
# defusedxml) into a self-contained virtualenv.
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install .


FROM python:3.14-slim@sha256:cea0e6040540fb2b965b6e7fb5ffa00871e632eef63719f0ea54bca189ce14a6

LABEL org.opencontainers.image.title="iso20022-bank-profile-mcp" \
      org.opencontainers.image.description="Local MCP server that manages, validates, and serves bank-specific ISO 20022 clearing profiles and rule packs." \
      org.opencontainers.image.source="https://github.com/sebastienrousseau/iso20022-bank-profile-mcp" \
      org.opencontainers.image.licenses="Apache-2.0"

# Non-root user (MCP clients launch the container with stdio; no extra
# privileges needed).
RUN groupadd --system mcp && useradd --system --gid mcp --home /home/mcp mcp \
    && mkdir -p /home/mcp \
    && chown -R mcp:mcp /home/mcp

COPY --from=builder /opt/venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER mcp
WORKDIR /home/mcp

# A non-zero exit here means an import / dependency mismatch; the MCP
# client will see it before the first tool call.
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import iso20022_bank_profile_mcp.server" || exit 1

ENTRYPOINT ["iso20022-bank-profile-mcp"]
