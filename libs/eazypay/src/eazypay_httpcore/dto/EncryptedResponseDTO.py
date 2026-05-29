  



from pydantic import BaseModel
from typing import Optional


class EncryptedResponseDTO(BaseModel):
    requestId: Optional[str] = ""
    service: Optional[str] = ""
    oaepHashingAlgorithm: Optional[str] = "" 
    iv: Optional[str] = ""
    encryptedKey: str
    encryptedData: str
    clientInfo: Optional[str] = "" 
    optionalParam: Optional[str] = ""
