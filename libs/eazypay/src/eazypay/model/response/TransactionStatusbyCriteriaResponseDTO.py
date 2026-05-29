  



from pydantic import BaseModel


class TransactionStatusbyCriteriaResponseDTO(BaseModel):
    merchantId: str
    terminalId: str
    merchantTranId: str
    subMerchantId: str
    OriginalBankRRN: str
    Amount: str
    payerVA: str
    response: str
    success: str
    message: str
    status: str
    TxnInitDate: str
    TxnCompletionDate: str
    UMN: str
    errormessage: str
