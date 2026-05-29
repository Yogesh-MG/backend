  



from pydantic import BaseModel
from typing import Optional

class CallbackStatus2RequestDTO(BaseModel):
    transactionType: str
    merchantId: str
    subMerchantId: str
    terminalId: str
    merchantTranId: Optional[str] = None
    transactionDate: Optional[str] = None
    BankRRN: Optional[str] = None
    refId: Optional[str] = None
