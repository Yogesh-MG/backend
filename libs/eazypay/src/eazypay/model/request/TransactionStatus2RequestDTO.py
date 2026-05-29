  



from pydantic import BaseModel


class TransactionStatus2RequestDTO(BaseModel):
    merchantId: str
    subMerchantId: str
    terminalId: str
    merchantTranId: str
