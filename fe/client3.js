document.addEventListener("alpine:init", () => {
  Alpine.data("client", () => ({
    eventSource: new EventSource("/stream"),
    conferenceStart: null,
    conferenceEnd: null,
    timers: [],

    mins: "00",
    secs: "00",

    barValue: 0,
    showBar: true,

    delay: false,
    countdownTimeout: undefined,
    
    // Proprietà reattiva per il layout di fine adunanza
    endMeetingMode: false,

    init() {
      console.log("v. 0.0.3 ~ Giuseppe Di Menna 2026");
      fetch("api/meeting")
        .then((res) => res.json())
        .then((data) => {
          if (data) {
            this.conferenceStart = stringToDate(data?.conferenceStart);
            this.conferenceEnd = stringToDate(data?.conferenceEnd);
            this.endMeetingMode = !!data?.endMeetingMode;
            this.timers = data?.timers.map((timer) => this.timerMapper(timer));
            this.startCountdown();
          }
        });

      this.eventSource.addEventListener("message", (e) => {
        const data = JSON.parse(e?.data);
        if (data && data.conferenceEnd && data.conferenceStart && data.timers?.length) {
          this.conferenceStart = stringToDate(data.conferenceStart);
          this.conferenceEnd = stringToDate(data.conferenceEnd);
          this.endMeetingMode = !!data.endMeetingMode;
          this.timers = data.timers.map((timer) => this.timerMapper(timer));
          this.startCountdown();
        }
      });
    },
    
    startCountdown(start = undefined, end = undefined, duration = undefined) {
      if (!!this.countdownTimeout && (!!this.isTimerActive || !!this.conferenceStart)) {
        clearTimeout(this.countdownTimeout);
      }
      if (this.isTimerActive) {
        const activeTimer = this.timers.find((timer) => timer.active);
        start = activeTimer.start.getTime();
        end = activeTimer.end.getTime();
        duration = activeTimer.duration;
        duration = Math.min(duration, (end - start) / 1000);
        end = Math.min(end, start + duration * 1000);
        end = new Date(end);
        this.updateCountdown(end, duration);
      } else if (!!this.conferenceStart) {
        end = this.conferenceStart;
        duration = (end.getTime() - Date.now()) / 1000;
        this.updateCountdown(end, duration);
      } else return;
    },

    updateCountdown(end, duration) {
      const now = new Date();
      let diff = Math.floor((end - now) / 1000);

      if (diff >= 0) {
        this.delay = false;
        this.showBar = true;
        this.mins = String(Math.floor(diff / 60)).padStart(2, "0");
        this.secs = String(diff % 60).padStart(2, "0");
        this.barValue = Math.floor(((Number(this.mins) * 60 + Number(this.secs)) * 100) / duration);
      } else {
        this.barValue = 0;
        this.showBar = !this.showBar;
        this.delay = true;
        diff = Math.abs(diff);
        this.mins = String(Math.floor(diff / 60)).padStart(2, "0");
        this.secs = String(diff % 60).padStart(2, "0");
      }

      this.countdownTimeout = setTimeout(() => this.updateCountdown(end, duration), 1000);
    },

    timerMapper(timer) {
      const startDate = stringToDate(timer.start);
      const endDate = timer.end ? stringToDate(timer.end) : new Date(startDate.getTime() + timer.maxDuration * 1000);
      return {
        id: timer.id,
        duration: timer.duration,
        maxDuration: timer.maxDuration,
        name: timer.name,
        active: timer.active,
        start: startDate,
        end: endDate,
      };
    },

    get isTimerActive() {
      return this.timers?.some((timer) => timer.active);
    },
    get activeTimer() {
      return this.timers?.find((timer) => timer.active);
    },
  }));
});

function stringToDate(timeString) {
  const now = new Date();
  if (timeString.length > 5) {
    const [hours, minutes, seconds] = timeString.split(":").map(Number);
    now.setHours(hours, minutes, seconds, 0);
  } else {
    const [hours, minutes] = timeString.split(":").map(Number);
    now.setHours(hours, minutes, 0, 0);
  }
  return now;
}