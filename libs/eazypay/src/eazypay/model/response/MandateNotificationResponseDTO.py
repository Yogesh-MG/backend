  



from pydantic import BaseModel


class MandateNotificationResponseDTO(BaseModel):
    merchantId: str
    terminalId: str
    merchantTranId: str
    subMerchantId: str
    amount: str
    response: str
    success: str
    message: str
    BankRRN: str
    errormessage: str
