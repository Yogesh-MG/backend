  



from pydantic import BaseModel


class CallbackStatus2ResponseDTO(BaseModel):
    merchantId: str
    terminalId: str
    merchantTranId: str
    response: str
    subMerchantId: str
    success: str
    message: str
    OriginalBankRRN: str
    payerVA: str
    Amount: str
    status: str
    TxnInitDate: str
    TxnCompletionDate: str
    refundRRN: str
    payerAccountType: str
    sequenceNum: str
    errormessage: str
