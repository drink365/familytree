
def wan(n):
    try:
        return int(round(float(n) / 10000.0))
    except Exception:
        return 0

def fmt_wan(n):
    return f"{wan(n):,} 萬元"

def fmt_currency(n, currency):
    try:
        return f"{int(n):,} {currency}"
    except Exception:
        return f"{n} {currency}"
