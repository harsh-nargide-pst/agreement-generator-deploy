from pydantic import BaseModel
from datetime import datetime
from typing import List, Dict


class AgreementRequest(BaseModel):
    owner_name: str
    owner_email: str
    tenant_details: list[dict]
    property_address: str
    city: str
    rent_amount: int
    agreement_period: list[datetime]
    owner_address: str
    furnishing_type: str
    security_deposit: int
    bhk_type: str
    area: int
    registration_date: str
    furniture_and_appliances: List[Dict[str, str]]
    amenities: List[str]
    user_id: str
    witness_details: List[Dict[str, str]]