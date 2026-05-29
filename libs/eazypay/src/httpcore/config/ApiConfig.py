  



from typing import Any, Dict

from pydantic import BaseModel


class ApiConfig(BaseModel):
    apiId: str
    apiName: str
    apiKey: str
    moduleName: str
    baseUrl: str
    basePath: str
    partnerId: str
    endpoint: str
    method: str
    requestDtoType: str
    responseDtoType: str
    category: str
    headers: Dict[str, Any]
