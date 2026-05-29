  



from pydantic import BaseModel


class RefundAPI12ResponseDTO(BaseModel):
    merchantId: str
    terminalId: str
    merchantTranId: str
    response: str
    subMerchantId: str
    success: str
    message: str
    originalBankRRN: str
    status: str
    refundRRN: str
    errormessage: str
