  



from pydantic import BaseModel


class BaseDTO(BaseModel):
    merchantId: str
    subMerchantId: str
    terminalId: str
    merchantTranId: str
