from __future__ import annotations

from pydantic import BaseModel



class RevokeMandateRequestDTO(BaseModel):
    merchantId: str
    subMerchantId: str
    terminalId: str
    merchantName: str
    subMerchantName: str
    payerVa: str
    amount: str
    note: str
    collectByDate: str
    merchantTranId: str
    billNumber: str
    requestType: str = "R"
    validityStartDate: str
    validityEndDate: str
    amountLimit: str
    remark: str
    frequency: str
    autoExecute: str = "N"
    debitDay: str
    debitRule: str
    revokable: str = "Y"
    blockfund: str
    purpose: str
    UMN: str