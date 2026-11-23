from datetime import date

from pydantic import BaseModel

from .offer_schemas import Money, Note, Ref


class ContractIn(BaseModel):
    contract_ref: Ref
    signed_on: date


class InvoiceIn(BaseModel):
    invoice_ref: Ref
    invoiced_cents: Money
    note: Note
