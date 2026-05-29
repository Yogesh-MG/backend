  



from typing import Any, Dict, List

from pydantic import BaseModel
from .ApiCategory import ApiCategory
from .ApiConfig import ApiConfig

class ModuleConfig(BaseModel):
    module: str
    baseUrl: str
    apiKey: str
    partnerId: str
    headers: Dict[str, Any]
    paymentTypes: List[ApiCategory]
    apis: List[ApiConfig]
