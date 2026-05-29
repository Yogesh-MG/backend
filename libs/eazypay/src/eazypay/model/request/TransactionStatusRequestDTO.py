  



from pydantic import BaseModel


class TransactionStatusRequestDTO(BaseModel):
    merchantId: str
    subMerchantId: str
    terminalId: str
    merchantTranId: str
