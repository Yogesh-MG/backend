  



from pydantic import BaseModel


class CreateMandateResponseDTO(BaseModel):
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
