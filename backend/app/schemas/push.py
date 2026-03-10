from pydantic import BaseModel


class PushChannelResponse(BaseModel):
    id: str
    name: str
    description: str
    enabled: bool


class PushRegisterRequest(BaseModel):
    token: str
    platform: str = "android"
    device_name: str = ""


class PushRegisterResponse(BaseModel):
    success: bool
    message: str
