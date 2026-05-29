  



from pydantic import BaseModel


class QRResponseDTO(BaseModel):
    merchantId: str
    terminalId: str
    merchantTranId: str
    subMerchantId: str
    success: str
    response: str
    status: str
    message: str
    originalBankRRN: str
    refId: str
    errormessage: str
