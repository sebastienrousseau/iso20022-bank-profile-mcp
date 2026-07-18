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

"""Shared fixtures for the iso20022-bank-profile-mcp test suite.

Provides sample ISO 20022 payloads and a bundled
:class:`ProfileEngine` fixture so the clearing-profile logic is exercised
end-to-end against the real baseline profiles.
"""

from __future__ import annotations

import pytest

from iso20022_bank_profile_mcp.engine import ProfileEngine

#: A pain.001 whose Cdtr address lacks Ctry and TwnNm -> two CBPR+ findings.
PAIN_001 = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.09">
  <CstmrCdtTrfInitn>
    <GrpHdr><MsgId>MSG-1</MsgId></GrpHdr>
    <PmtInf>
      <Cdtr>
        <Nm>Acme Ltd</Nm>
        <PstlAdr><StrtNm>Main St</StrtNm></PstlAdr>
      </Cdtr>
    </PmtInf>
  </CstmrCdtTrfInitn>
</Document>
"""

#: The same pain.001 with a fully structured address (no CBPR+ findings).
PAIN_001_COMPLIANT = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.09">
  <CstmrCdtTrfInitn>
    <GrpHdr><MsgId>MSG-2</MsgId></GrpHdr>
    <PmtInf>
      <Cdtr>
        <Nm>Acme Ltd</Nm>
        <PstlAdr>
          <StrtNm>Main St</StrtNm>
          <TwnNm>London</TwnNm>
          <Ctry>GB</Ctry>
        </PstlAdr>
      </Cdtr>
    </PmtInf>
  </CstmrCdtTrfInitn>
</Document>
"""

#: A pain.001 whose Ctry/TwnNm elements are present but empty (text is None),
#: exercising the ``node.text is not None`` guard in ``_find_text``.
PAIN_001_EMPTY_CTRY = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.09">
  <CstmrCdtTrfInitn>
    <PmtInf>
      <Cdtr>
        <PstlAdr>
          <TwnNm></TwnNm>
          <Ctry></Ctry>
        </PstlAdr>
      </Cdtr>
    </PmtInf>
  </CstmrCdtTrfInitn>
</Document>
"""

#: A SEPA-style payment in EUR whose ChrgBr is not SLEV (violates SEPA rule).
SEPA_EUR_BAD = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.09">
  <CstmrCdtTrfInitn>
    <PmtInf>
      <Ccy>EUR</Ccy>
      <ChrgBr>DEBT</ChrgBr>
    </PmtInf>
  </CstmrCdtTrfInitn>
</Document>
"""

#: The same SEPA payment with a compliant SLEV charge bearer.
SEPA_EUR_GOOD = SEPA_EUR_BAD.replace("DEBT", "SLEV")

#: A non-EUR payment: the SEPA conditional rule does not apply at all.
SEPA_USD = SEPA_EUR_BAD.replace("EUR", "USD")

#: A payload that is not well-formed XML at all.
NOT_XML = "definitely not xml <<<"


@pytest.fixture
def engine() -> ProfileEngine:
    """The bundled clearing-profile engine (five bundled profiles)."""
    return ProfileEngine.from_bundled()
