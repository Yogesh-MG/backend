  



from pydantic import BaseModel


class QR2RequestDTO(BaseModel):
    amount: str
    terminalId: str
    billNumber: str
    merchantId: str
    # subMerchantId: str
    merchantTranId: str
