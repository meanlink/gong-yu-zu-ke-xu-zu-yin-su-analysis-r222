from datetime import date
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, Field, StringConstraints

Note = Annotated[str, StringConstraints(strip_whitespace=True, min_length=4, max_length=300)]
PositiveId = Annotated[int, Field(gt=0)]


class RemedyIn(BaseModel):
    task_id: PositiveId
    event_id: PositiveId
    promise_due: date
    tenant_impact: Note


class ReviewNote(BaseModel):
    note: Note


class CheckoutIn(BaseModel):
    task_id: PositiveId
    starts_at: AwareDatetime
    duration_minutes: Literal[30, 60, 90]
    instructions: Note


class InspectionIn(BaseModel):
    inspection_reference: Note
    returned_keys: int = Field(ge=0, le=20)
    unit_condition: Literal['ready', 'repair']


class OutcomeIn(BaseModel):
    task_id: PositiveId
    result: Literal['renewed', 'moved_out']
    new_lease_end: date | None = None
    supporting_reference: Note
