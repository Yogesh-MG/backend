  



from pydantic import BaseModel


class ExecuteMandateResponseDTO(BaseModel):
    merchantId: str
    terminalId: str
    merchantTranId: str
    subMerchantId: str
    Amount: str
    response: str
    success: str
    message: str
    BankRRN: str
    errormessage: str
