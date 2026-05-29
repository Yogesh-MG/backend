  



from pydantic import BaseModel


class CallbackStatus1RequestDTO(BaseModel):
    BankRRN: str
    refId: str
    TransactionDate: str
    transactionType: str
    merchantId: str
    subMerchantId: str
    terminalId: str
    merchantTranId: str
