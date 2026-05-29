  



from pydantic import BaseModel


class ValidateVoucherResponseDTO(BaseModel):
    merchantId: str
    terminalId: str
    merchantTranId: str
    subMerchantId: str
    success: str
    response: str
    message: str
    BankRRN: str
