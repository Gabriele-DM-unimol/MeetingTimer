import time

from templates_service import WEEKDAY_TEMPLATE, WEEKEND_TEMPLATE
from time_utils import format_seconds_as_time, parse_time_to_seconds


class MeetingService:
    def __init__(self, meeting_store, template_service):
        self.meeting_store = meeting_store
        self.template_service = template_service

    def load_current(self):
        meeting = self.meeting_store.load()
        return meeting if meeting else self.reset_to_default()

    def reset_to_default(self):
        meeting = self.refresh(self.get_default())
        self.meeting_store.save(meeting)
        return meeting

    def get_default(self):
        template_name = WEEKDAY_TEMPLATE if time.localtime().tm_wday < 5 else WEEKEND_TEMPLATE
        templates = self.template_service.build_catalog()
        meeting = next(template for template in templates if template["name"] == template_name)
        meeting.setdefault("endMeetingMode", False)
        return meeting

    def save(self, meeting):
        refreshed = self.refresh(meeting)
        self.meeting_store.save(refreshed)
        self.template_service.save_template_times(refreshed)
        return refreshed

    def refresh(self, meeting):
        timers = meeting["timers"]
        conference_start = parse_time_to_seconds(meeting.get("conferenceStart") or timers[0]["start"])
        active_index = self._active_timer_index(timers)

        if active_index is None:
            self._refresh_linear_timeline(timers, conference_start)
            return meeting

        self._complete_missing_past_times(timers[:active_index], conference_start)
        self._refresh_active_and_future_timeline(timers, active_index)
        return meeting

    @staticmethod
    def _active_timer_index(timers):
        return next((index for index, timer in enumerate(timers) if timer["active"]), None)

    @staticmethod
    def _timer_nominal_duration(timer):
        return timer.get("duration", timer.get("maxDuration", 60))

    def _refresh_linear_timeline(self, timers, conference_start):
        current_time = conference_start
        for timer in timers:
            timer["start"] = format_seconds_as_time(current_time)
            current_time += self._timer_nominal_duration(timer)
            timer["end"] = format_seconds_as_time(current_time)

    def _complete_missing_past_times(self, past_timers, conference_start):
        for timer in past_timers:
            if not timer.get("start"):
                timer["start"] = format_seconds_as_time(conference_start)
            if not timer.get("end"):
                timer["end"] = format_seconds_as_time(
                    parse_time_to_seconds(timer["start"]) + timer["duration"]
                )

    @staticmethod
    def _refresh_active_and_future_timeline(timers, active_index):
        current_time = parse_time_to_seconds(timers[active_index]["start"])
        for timer in timers[active_index:]:
            timer["start"] = format_seconds_as_time(current_time)
            current_time += timer["duration"]
            timer["end"] = format_seconds_as_time(current_time)
