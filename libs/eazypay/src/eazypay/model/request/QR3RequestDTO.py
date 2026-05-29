  



from pydantic import BaseModel
from typing import Optional


class QR3RequestDTO(BaseModel):
    terminalId: str
    amount: str
    billNumber: str
    validatePayerAccFlag: Optional[str] = None
    payerAccount: Optional[str] = None
    payerIFSC: Optional[str] = None
    signedIntentFlag: Optional[str] = None
    merchantId: str
    # subMerchantId: str
    merchantTranId: str


    validityStartDateTime: Optional[str] = None
    validityEndDateTime: Optional[str] = None
    refid: Optional[str] =None
    update: Optional[str] = None
