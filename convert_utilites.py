from datetime import datetime, timedelta


def timedelta_to_hms_str(td):
    hours, remainder = divmod(td.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)
    return "{:02}:{:02}:{:02}".format(int(hours), int(minutes), int(seconds))


def hms_str_to_timedelta(hms_str):
    parts = list(map(int, hms_str.split(':')))
    if len(parts) == 3:
        hours, minutes, seconds = parts
    elif len(parts) == 2:
        hours, minutes = parts
        seconds = 0
    else:
        raise ValueError(f"Invalid format for hms_str: {hms_str}")
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)


def calculate_elapsed_time(start_time_str, paused_time_str):
    start_time = datetime.strptime(start_time_str, '%d/%m/%Y %H:%M:%S')
    paused_time = datetime.strptime(paused_time_str, '%d/%m/%Y %H:%M:%S')
    return paused_time - start_time


def convert_iso_to_standard_format(iso_time_str):
    dt = datetime.fromisoformat(iso_time_str)
    return dt.strftime('%d/%m/%Y %H:%M:%S')


def convert_text_to_iso(date_str):
    dt = datetime.strptime(date_str, '%d/%m/%Y %H:%M:%S')
    return dt.isoformat()


def remove_seconds_for_notion(times_str):
    """Convert each line in a multi-line time string from '%d/%m/%Y %H:%M:%S' to '%d/%m/%Y %H:%M'."""
    if not times_str:
        return times_str
    lines = times_str.split('\n')
    new_lines = []
    for line in lines:
        try:
            dt = datetime.strptime(line, '%d/%m/%Y %H:%M:%S')
            new_lines.append(dt.strftime('%d/%m/%Y %H:%M'))
        except ValueError:
            new_lines.append(line)
    return "\n".join(new_lines)


def get_last_full_timestamp_from_db(db_value):
    """
    Parse a multi-line or space-delimited DB string for start_time/paused_time.
    Return the last token/line that matches the format '%d/%m/%Y %H:%M:%S'.
    If none match, returns the final token/line as a fallback.
    """
    if not db_value:
        return None

    # Split by newline if your DB stores each new start_time on its own line:
    lines = db_value.split('\n')

    # If your DB is storing them in a single line separated by spaces, do this instead:
    # lines = db_value.split()

    # Start from the end and find the first line (in reverse) that fully matches the datetime format with seconds.
    for line in reversed(lines):
        candidate = line.strip()
        try:
            datetime.strptime(candidate, '%d/%m/%Y %H:%M:%S')
            return candidate  # Return the first valid match going backward
        except ValueError:
            continue

    # If none matched the exact format, return the last line anyway to avoid losing data
    return lines[-1].strip()

