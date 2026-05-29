from __future__ import annotations

from pydantic import BaseModel


class UpdateMandateRequestDTO(BaseModel):
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
    validityStartDate: str
    validityEndDate: str
    amountLimit: str
    remark: str
    requestType: str = "U"  # Default value is "U"
    frequency: str
    autoExecute: str = "N"  # Default value is "N"
    debitDay: str
    debitRule: str
    revokable: str
    blockfund: str
    purpose: str
    UMN: str  
