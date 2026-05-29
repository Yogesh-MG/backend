  



from pydantic import BaseModel


class TransactionStatus3ResponseDTO(BaseModel):
    merchantId: str
    terminalId: str
    merchantTranId: str
    response: str
    subMerchantId: str
    OriginalBankRRN: str
    Amount: str
    success: str
    message: str
    status: str
    payerAccountType: str
    sequenceNum: str
    errormessage: str
