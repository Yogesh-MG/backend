from __future__ import annotations
from pydantic import BaseModel


class RevokeMandateResponseDTO(BaseModel):
    merchantId: str
    terminalId: str
    merchantTranId: str
    response: str
    subMerchantId: str
    success: str
    message: str
    merchantTranId: str
    BankRRN: str