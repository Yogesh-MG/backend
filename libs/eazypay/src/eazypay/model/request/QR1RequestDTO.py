  



from pydantic import BaseModel


class QR1RequestDTO(BaseModel):
    terminalId: str
    amount: str
    billNumber: str
    billNumber2: str
    merchantId: str
    # subMerchantId: str
    merchantTranId: str
