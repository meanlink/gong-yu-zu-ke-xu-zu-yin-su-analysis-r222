from calendar import monthrange
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

LOCAL = ZoneInfo('Asia/Shanghai')


def today():
    return datetime.now(LOCAL).date()


def lease_end(start, months):
    month_number = start.year * 12 + start.month - 1 + months
    year, month = divmod(month_number, 12)
    month += 1
    last = monthrange(year, month)[1]
    anniversary = date(year, month, min(start.day, last))
    # A 29th–31st anniversary falling outside its month closes at that month's end.
    return anniversary if start.day > last else anniversary - timedelta(days=1)


def first_invoice(start, monthly_cents):
    days = monthrange(start.year,start.month)[1]
    remaining = days - start.day + 1
    # Round half up in cents using integer arithmetic.
    return date(start.year,start.month,days), (2 * monthly_cents * remaining + days) // (2 * days)
