  



from pydantic import BaseModel
from typing import Optional

class CreateMandateRequestDTO(BaseModel):
    merchantName: str
    subMerchantName: str
    payerVa: str
    amount: str
    note: str
    collectByDate: str
    billNumber: str
    validityStartDate: str
    validityEndDate: str
    amountLimit: str
    remark: str
    requestType: str
    frequency: str
    autoExecute: str
    debitDay: str
    debitRule: str
    revokable: str
    blockfund: str
    purpose: str
    merchantId: str
    subMerchantId: str
    terminalId: str
    merchantTranId: str

    validatePayerAccFlag: Optional[str] = None
    payerAccount: Optional[str] = None 
    payerIFSC: Optional[str] = None 
