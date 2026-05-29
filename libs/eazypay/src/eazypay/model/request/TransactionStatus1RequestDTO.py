  



from pydantic import BaseModel


class TransactionStatus1RequestDTO(BaseModel):
    merchantId: str
    subMerchantId: str
    terminalId: str
    merchantTranId: str
