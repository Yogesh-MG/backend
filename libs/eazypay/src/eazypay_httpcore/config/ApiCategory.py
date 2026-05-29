  



from pydantic import BaseModel


class ApiCategory(BaseModel):
    name: str
    apiKey: str
    partnerId: str
    priority: str
