  



from pydantic import BaseModel


class CreateVouchersRequestDTO(BaseModel):
    beneficiaryID: str
    mobileNumber: str
    beneficiaryName: str
    amount: str
    expiry: str
    purposeCode: str
    mcc: str
    VoucherRedemptionType: str
    PayerVA: str
    type: str
    merchantId: str
    subMerchantId: str
    terminalId: str
    merchantTranId: str
