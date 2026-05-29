  



from pydantic import BaseModel


class RedeemVoucherResponseDTO(BaseModel):
    merchantId: str
    terminalId: str
    merchantTranId: str
    subMerchantId: str
    success: str
    response: str
    message: str
    BankRRN: str
    Amount: str
    UUID: str
    UMN: str
    errormessage: str
