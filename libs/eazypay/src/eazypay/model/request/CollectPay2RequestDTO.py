  



from pydantic import BaseModel


class CollectPay2RequestDTO(BaseModel):
    note: str
    amount: str
    collectByDate: str
    payerVa: str
    billNumber: str
    subMerchantName: str
    merchantName: str
    merchantId: str
    subMerchantId: str
    terminalId: str
    merchantTranId: str
