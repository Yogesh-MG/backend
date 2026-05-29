  



from pydantic import BaseModel


class CollectPayRequestDTO(BaseModel):
    amount: str
    payerVa: str
    note: str
    collectByDate: str
    merchantName: str
    subMerchantName: str
    billNumber: str
    validatePayerAccFlag: str
    payerAccount: str
    payerIFSC: str
    merchantId: str
    subMerchantId: str
    terminalId: str
    merchantTranId: str
