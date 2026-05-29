  



from pydantic import BaseModel


class CreateVoucherResponseDTO(BaseModel):
    merchantId: str
    terminalId: str
    merchantTranId: str
    subMerchantId: str
    response: str
    success: str
    message: str
    Amount: str
    expiryDate: str
    UMN: str
    UUID: str
    status: str
    errormessage: str
