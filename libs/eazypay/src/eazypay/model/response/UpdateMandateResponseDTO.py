from __future__ import annotations
from pydantic import BaseModel


class UpdateMandateResponseDTO(BaseModel):
    response: str
    merchantId: str
    subMerchantId: str
    terminalId: str
    success: str
    message: str
    merchantTranId: str
    bankRRN: str