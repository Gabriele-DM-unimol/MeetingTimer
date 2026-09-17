def parse_time_to_seconds(time_value):
    if not time_value:
        return 0

    hours, minutes, seconds = map(int, time_value.split(":"))
    return hours * 3600 + minutes * 60 + seconds


def format_seconds_as_time(seconds):
    normalized = int(seconds)
    hours = normalized // 3600
    minutes = (normalized % 3600) // 60
    remaining_seconds = normalized % 60
    return f"{hours:02}:{minutes:02}:{remaining_seconds:02}"
