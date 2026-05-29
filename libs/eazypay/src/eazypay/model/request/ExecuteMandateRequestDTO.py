  



from pydantic import BaseModel
from typing import Optional

class ExecuteMandateRequestDTO(BaseModel):
    merchantName: str
    subMerchantName: str
    amount: str
    billNumber: str
    remark: str
    UMN: str
    purpose: str
    merchantId: str
    subMerchantId: str
    terminalId: str
    merchantTranId: str
    
    retryCount: Optional[str] = ""
    mandateSeqNo: Optional[str] = ""
