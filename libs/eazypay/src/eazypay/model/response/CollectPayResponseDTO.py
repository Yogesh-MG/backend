  



from pydantic import BaseModel, Field


class CollectPayResponseDTO(BaseModel):
    merchantId: str
    terminalId: str
    merchantTranId: str
    subMerchantId: str
    success: str
    response: str
    status: str
    message: str
    originalBankRRN: str
    BankRRN: str
    errormessage: str


class CollectPay123ResponseDTO(BaseModel):
    merchantId: str = Field(alias="merchantId")
    terminalId: str = Field(alias="terminalId")
    merchantTranId: str = Field(alias="merchantTranId")
    subMerchantId: str = Field(alias="subMerchantId")
    response: str = Field(alias="response")
    success: str = Field(alias="success")
    message: str = Field(alias="message")
    bankRRN: str = Field(alias="BankRRN")  # Case sensitive
    amount: str = Field(alias="Amount")      # Case sensitive
    errormessage: str = Field(alias="errormessage")
