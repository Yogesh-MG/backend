  



from pydantic import BaseModel
from typing import Optional


class CollectPay3RequestDTO(BaseModel):
    note: str
    amount: str
    collectByDate: str
    payerVa: str
    billNumber: str
    subMerchantName: str
    merchantName: str
    merchantId: str
    subMerchantId: str
    terminalId: str
    merchantTranId: str

    validatePayerAccFlg: Optional[str] = None
    payerIFSC: Optional[str] = None
    payerAccount: Optional[str] = None