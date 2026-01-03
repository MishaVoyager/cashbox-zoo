from typing import Optional

from pydantic import BaseModel, ConfigDict

from domain.models import Resource


class ReturnResourceDto(BaseModel):
    model_config = ConfigDict(
        extra='ignore',
        arbitrary_types_allowed=True
    )

    resource: Resource
    previous_visitor_email: str
    new_visitor_email: Optional[str] = None
