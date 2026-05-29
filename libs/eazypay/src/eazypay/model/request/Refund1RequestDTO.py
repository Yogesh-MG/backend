  



from pydantic import BaseModel
from typing import Optional


class Refund1RequestDTO(BaseModel):
    originalBankRRN: str
    originalmerchantTranId: str
    refundAmount: str
    note: str
    onlineRefund: str
    merchantId: str
    subMerchantId: str
    terminalId: str
    merchantTranId: str
    
    payeeVA: Optional[str] = ""
