  



from pydantic import BaseModel


class CallbackStatus1ResponseDTO(BaseModel):
    merchantId: str
    terminalId: str
    merchantTranId: str
    response: str
    subMerchantId: str
    success: str
    message: str
    OriginalBankRRN: str
    payerVA: str
    amount: str
    status: str
    TxnInitDate: str
    TxnCompletionDate: str
    refundRRN: str
    errormessage: str
