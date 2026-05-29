  



from pydantic import BaseModel


class MandateNotificationRequestDTO(BaseModel):
    payerVa: str
    amount: str
    note: str
    executionDate: str
    mandateSeqNo: str
    key: str
    value: str
    merchantId: str
    subMerchantId: str
    terminalId: str
    merchantTranId: str
