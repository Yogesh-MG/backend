  



from pydantic import BaseModel


class RefundStatusResponseDTO(BaseModel):
    merchantId: str
    terminalId: str
    merchantTranId: str
    subMerchantId: str
    success: str
    response: str
    status: str
    message: str
    originalBankRRN: str
    errormessage: str
