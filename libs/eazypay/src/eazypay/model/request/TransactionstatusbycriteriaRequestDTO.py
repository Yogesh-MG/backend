  



from pydantic import BaseModel
from typing import Optional


class TransactionstatusbycriteriaRequestDTO(BaseModel):
    transactionType: str
    UMN: str
    merchantId: str
    subMerchantId: str
    terminalId: str
    
    merchantTranId: Optional[str] = None
    transactionDate: Optional[str] = None
    BankRRN: Optional[str] = None
    refID: Optional[str] = None
    
    
