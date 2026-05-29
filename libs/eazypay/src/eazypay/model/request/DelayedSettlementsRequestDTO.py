  



from pydantic import BaseModel


class DelayedSettlementsRequestDTO(BaseModel):
    UUID: str
    merchantId: str
    subMerchantId: str
    merchantTranId: str
