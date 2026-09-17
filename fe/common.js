window.TimerAppUtils = {
  stringToDate(timeString) {
    const now = new Date();
    if (!timeString) return now;

    const [hours, minutes, seconds = 0] = timeString.split(":").map(Number);
    now.setHours(hours, minutes, seconds, 0);
    return now;
  },

  secondsToMinutesString(seconds) {
    return `${Math.floor(seconds / 60).toString().padStart(2, "0")}:${(seconds % 60)
      .toString()
      .padStart(2, "0")}`;
  },

  getClockObj() {
    const now = new Date();
    return {
      hm: now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      s: String(now.getSeconds()).padStart(2, "0"),
    };
  },

  getEndMeetingGreeting(clock) {
    const hour = Number(clock.hm.slice(0, 2));
    return hour >= 14 ? "BUONA SERATA" : "BUONA GIORNATA";
  },
};
