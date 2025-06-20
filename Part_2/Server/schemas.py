from pydantic import BaseModel, Field
from typing import List, Dict, Any


class Request(BaseModel):
    history: List[Dict[str, str]] = Field(default_factory=list)
    user_info: Dict[str, Any] | None = None
    user_msg: str

class Response(BaseModel):
    assistant_msg: str
    user_info: Dict[str, Any] | None = None

class UserInfoResponse(BaseModel):
    first_name: str = Field(description="שם פרטי")
    last_name: str = Field(description="שם משפחה")
    id_number: str = Field(description="מספר זהות - 9 ספרות")
    gender: str = Field(description="מין - זכר/נקבה")
    age: int = Field(description="גיל")
    hmo_name: str = Field(description="קופת חולים - מכבי/מאוחדת/כללית")
    card_number: str = Field(description="מספר כרטיס קופה - 9 ספרות")
    tier: str = Field(description="רמת ביטוח - זהב/כסף/ארד")
    assistant_message: str = Field(description="הודעת העוזר למשתמש")
    collection_complete: bool = Field(description="האם איסוף הפרטים הושלם")

class VerificationResponse(BaseModel):
    first_name: str
    last_name: str
    id_number: str
    gender: str
    age: int
    hmo_name: str
    card_number: str
    tier: str
    assistant_message: str = Field(description="הודעת העוזר למשתמש")
    verification_complete: bool = Field(description="האם האימות הושלם")
    verified: bool = Field(default=False, description="האם הפרטים אומתו")