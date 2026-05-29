  



from pydantic import BaseModel


class QR123ResponseDTO(BaseModel):
    merchantId: str
    terminalId: str
    merchantTranId: str
    response: str
    success: str
    message: str
    refId: str
    errormessage: str
