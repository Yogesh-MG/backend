  



from pydantic import BaseModel


class ValidateVoucherRequestDTO(BaseModel):
    merchantName: str
    subMerchantName: str
    MCC: str
    amount: str
    txnNote: str
    validityStartDate: str
    validityEndDate: str
    amRule: str
    UMN: str
    pa: str
    sign: str
    orgId: str
    mode: str
    purpose: str
    merchantId: str
    subMerchantId: str
    terminalId: str
    merchantTranId: str
