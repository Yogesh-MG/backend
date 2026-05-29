  



from pydantic import BaseModel


class Refund2RequestDTO(BaseModel):
    originalBankRRN: str
    originalmerchantTranId: str
    payeeVA: str
    refundAmount: str
    note: str
    onlineRefund: str
    merchantId: str
    subMerchantId: str
    terminalId: str
    merchantTranId: str
