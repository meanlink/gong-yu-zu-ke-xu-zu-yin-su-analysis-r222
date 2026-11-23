from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

Ref = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)]
Note = Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=400)]
Money = Annotated[int, Field(ge=0, le=1_000_000_000)]


class BudgetIn(BaseModel):
    neighborhood: Ref
    starts_month: date
    cap_cents: Money
    justification: Note


class OfferIn(BaseModel):
    task_id: int = Field(gt=0)
    ref: Ref
    term_months: int = Field(ge=2, le=18)
    monthly_discount_cents: Money
    valid_through: date
    rationale: Note


class OfferAction(BaseModel):
    decision: Literal['issue','decline','withdraw']
    note: Note
