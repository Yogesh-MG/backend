  



from pydantic import BaseModel


class QRRequestDTO(BaseModel):
    amount: str
    update: str
    validityStartDateTime: str
    signedIntentFlag: str
    payerAccount: str
    validityEndDateTime: str
    payerIFSC: str
    ValidatePayerAccFlag: str
    refId: str
    billNumber: str
    merchantId: str
    # subMerchantId: str
    terminalId: str
    merchantTranId: str
