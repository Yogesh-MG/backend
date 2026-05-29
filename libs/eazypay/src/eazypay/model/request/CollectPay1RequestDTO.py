  



from pydantic import BaseModel


class CollectPay1RequestDTO(BaseModel):
    note: str
    amount: str
    collectByDate: str
    payerVa: str
    terminalId: str
    billNumber: str
    subMerchantName: str
    merchantName: str
    merchantId: str
    subMerchantId: str
    merchantTranId: str
