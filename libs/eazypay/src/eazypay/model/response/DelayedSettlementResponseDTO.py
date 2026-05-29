  



from pydantic import BaseModel


class DelayedSettlementResponseDTO(BaseModel):
    merchantId: str
    terminalId: str
    merchantTranId: str
    response: str
    message: str
    Amount: str
    errormessage: str
