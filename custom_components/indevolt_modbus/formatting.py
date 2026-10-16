"""Format documented decimal versions and byte-packed clock fields."""


def format_register_value(value: int, display_format: str) -> str | None:
    """Present a raw uint16 without guessing invalid packed clock values."""
    if not 0 <= value <= 65535:
        return None
    if display_format == "firmware":
        return f"V{value // 10000}.{value // 100 % 100:02d}.{value % 100:02d}"
    if display_format == "inverter_version":
        return f"V{value // 100}.{value % 100:02d}"
    if display_format == "protocol_version":
        return f"V{value // 10}.{value % 10}"
    high, low = divmod(value, 256)
    if display_format == "year_month":
        return f"{2000 + high:04d}-{low:02d}" if high <= 99 and 1 <= low <= 12 else None
    if display_format == "day_hour":
        return f"Day {high}, hour {low:02d}" if 1 <= high <= 31 and low <= 23 else None
    if display_format == "hour_minute":
        return f"{high:02d}:{low:02d}" if high <= 23 and low <= 59 else None
    if display_format == "minute_second":
        return f"{high:02d}:{low:02d}" if high <= 59 and low <= 59 else None
    raise ValueError(f"Unknown register display format: {display_format}")
