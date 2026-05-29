  



from pydantic import BaseModel


class TransactionStatus12ResponseDTO(BaseModel):
    merchantId: str
    terminalId: str
    merchantTranId: str
    response: str
    subMerchantId: str
    OriginalBankRRN: str
    amount: str
    success: str
    message: str
    status: str
    errormessage: str
