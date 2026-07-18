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

"""The error taxonomy: stable codes and serializable ``to_detail`` output."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from iso20022_bank_profile_mcp.errors import (
    BankProfileError,
    ErrorDetail,
    InvalidInputError,
    InvalidProfileDefinitionError,
    UnknownProfileError,
)


@pytest.mark.parametrize(
    ("cls", "code"),
    [
        (BankProfileError, "BP_ERROR"),
        (InvalidInputError, "BP_INVALID_INPUT"),
        (UnknownProfileError, "BP_UNKNOWN_PROFILE"),
        (InvalidProfileDefinitionError, "BP_INVALID_PROFILE_DEFINITION"),
    ],
)
def test_subclass_code_and_to_detail(
    cls: type[BankProfileError], code: str
) -> None:
    """Each subclass carries its code through to a serializable detail."""
    exc = cls("boom", locator="/here", context={"k": "v"})
    detail = exc.to_detail()
    assert isinstance(detail, ErrorDetail)
    assert detail.code == code
    assert detail.locator == "/here"
    assert detail.explanation == "boom"
    assert detail.context == {"k": "v"}


def test_error_defaults() -> None:
    """Locator defaults to ``/`` and context to an empty dict."""
    exc = BankProfileError("nope")
    assert exc.locator == "/"
    assert exc.context == {}
    assert str(exc) == "nope"


def test_subclasses_are_bank_profile_errors() -> None:
    """Every concrete error is a specialisation of ``BankProfileError``."""
    for cls in (
        InvalidInputError,
        UnknownProfileError,
        InvalidProfileDefinitionError,
    ):
        assert issubclass(cls, BankProfileError)


def test_error_detail_locator_default() -> None:
    """A bare :class:`ErrorDetail` defaults its locator to ``/``."""
    detail = ErrorDetail(code="X", explanation="e")
    assert detail.locator == "/"
    assert detail.context == {}


def test_error_detail_is_frozen() -> None:
    """:class:`ErrorDetail` is immutable (``frozen=True``)."""
    detail = ErrorDetail(code="X", explanation="e")
    with pytest.raises(ValidationError):
        detail.code = "Y"  # type: ignore[misc]
