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