  



from pydantic import BaseModel


class RedeemVoucherRequestDTO(BaseModel):
    merchantName: str
    subMerchantName: str
    MCC: str
    amount: str
    txnNote: str
    UUID: str
    UMN: str
    OTP: str
    note: str
    merchantId: str
    subMerchantId: str
    terminalId: str
    merchantTranId: str
