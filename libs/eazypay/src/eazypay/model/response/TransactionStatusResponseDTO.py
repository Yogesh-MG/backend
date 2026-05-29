  



from pydantic import BaseModel


class TransactionStatusResponseDTO(BaseModel):
    merchantId: str
    terminalId: str
    merchantTranId: str
    subMerchantId: str
    OriginalBankRRN: str
    Amount: str
    response: str
    success: str
    message: str
    status: str
    UMN: str
    sequenceNum: str
    payerAccountType: str
    errormessage: str
