  



from pydantic import BaseModel


class TransactionStatus3RequestDTO(BaseModel):
    merchantId: str
    subMerchantId: str
    terminalId: str
    merchantTranId: str
