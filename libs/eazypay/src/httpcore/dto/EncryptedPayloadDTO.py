  



from pydantic import BaseModel
from typing import Union


class EncryptedPayloadDTO(BaseModel):
    requestId: str
    service: str
    encryptedKey: str
    oaepHashingAlgorithm: Union[str, None] = "NONE"
    iv: str
    encryptedData: str
    clientInfo: str
    optionalParam: str
