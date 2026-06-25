/*struttura timer
BE:
{
  id: number;
  name: string;
  start: string [[hh:mm:ss]];
  end: string [[hh:mm:ss]];
  duration: number [[secs]];
  maxDuration: number [[secs]];
  active: boolean;
}
FE:
{
  id: number;
  name: string;
  start: Date;
  end: Date;
  duration: number [[secs]];
  maxDuration: number [[secs]];
  active: boolean;
}

*/

document.addEventListener("alpine:init", () => {
  Alpine.data("admin", () => ({
    min: 1,
    max: 45,
    modalIsOpen: false,

    // info adunanza
    conferenceStart: undefined,

    set conferenceStartVal(value) {
      this.conferenceStart = stringToDate(value);
    },

    get conferenceStartVal() {
      return this.conferenceStart?.toTimeString().slice(0, 5);
    },

    conferenceEnd: undefined,
    set conferenceEndVal(value) {
      this.conferenceEnd = stringToDate(value);
    },

    get conferenceEndVal() {
      return this.conferenceEnd?.toTimeString().slice(0, 5);
    },

    timers: [],

    insertingDuration: 10,
    insertingName: "Parte",

    mins: "00",
    secs: "00",

    barValue: 0,
    showBar: true,

    templates: [],
    selectedTemplateId: undefined,
    initialTemplateId: undefined,

    endDate: new Date(),
    eventSource: new EventSource("/stream"),
    delay: false,
    countdownTimeout: undefined,

    loading: false,

    init() {
      console.log("v. 0.0.2 ~ Giuseppe Di Menna 19/02/2025");
      this.$watch("selectedTemplateId", (value, oldValue) => {
        // Esegui l'applyTemplate SOLO se non è il primo rendering (oldValue deve esistere)
        if (oldValue !== undefined && value !== oldValue) {
        this.applyTemplate();
        }
      });;

      this.$watch("conferenceStart", (value, oldValue) => {
        if (
          value?.toTimeString().slice(0, 5) !==
          oldValue?.toTimeString().slice(0, 5)
        ) {
          this.startCountdown();
        }
      });
fetch("/api/templates")
        .then((res) => res.json())
        .then((data) => {
          this.templates = data;
        })
        .then(() => {
          fetch("/api/meeting/start")
            .then((res) => res.json())
            .then((data) => {
              // SALVIAMO L'ID QUI
              this.initialTemplateId = data.id; 
              this.selectedTemplateId = data.id;
            })
            .then(() => {
              fetch("api/meeting")
                .then((res) => res.json())
                .then((data) => {
                  if (data) {
                    this.conferenceStart = stringToDate(data?.conferenceStart);
                    this.conferenceEnd = stringToDate(data?.conferenceEnd);
                    this.timers = data?.timers.map((timer) =>
                      this.timerMapper(timer)
                    );
                    this.startCountdown();
                  }
                });
            });
        });

      this.eventSource.addEventListener("message", (e) => {
        data = JSON.parse(e?.data);
        if (
          data &&
          data.conferenceEnd &&
          data.conferenceStart &&
          data.timers?.length
        ) {
          this.conferenceStart = stringToDate(data.conferenceStart);
          this.conferenceEnd = stringToDate(data.conferenceEnd);
          this.timers = data.timers.map((timer) => this.timerMapper(timer));
          this.startCountdown();
        }
      });
    },

    addTimer() {
      this.timers.push({
        id:
          Math.max.apply(
            Math,
            this.timers.map((timer) => timer.id)
          ) + 1,
        duration: this.insertingDuration * 60,
        maxDuration: this.insertingDuration * 60,
        name: this.insertingName,
        active: false,
      });
      this.insertingDuration = 10;
      this.insertingName = "Parte";
      this.postTimers();
    },

    get calculatedEnd() {
      forward = this.slicedTimers[1];
      if (forward.length > 0) {
        start = forward[0].start;
        return new Date(
          start.getTime() +
            forward.map((timer) => timer.duration).reduce((a, b) => a + b, 0) *
              1000
        )
          .toTimeString()
          .slice(0, 5);
      }
      return this.conferenceEnd?.toTimeString().slice(0, 5);
    },

    get meetingInDelay() {
      const calculatedEnd = stringToDate(this.calculatedEnd).getTime();
      return this.conferenceEnd.getTime() < calculatedEnd;
    },

    get effectiveStart() {
      return this.timers[0]?.start?.toTimeString().slice(0, 5);
    },

    handle(item, position) {
      let arr = [...this.slicedTimers[1]];
      let index = arr.findIndex((timer) => timer.id === item);

      if (index === -1 || position < 0 || position >= arr.length) return;

      // Rimuove l'elemento dalla sua posizione originale
      let [removed] = arr.splice(index, 1);

      // Inserisce l'elemento nella nuova posizione
      arr.splice(position, 0, removed);

      // Ricostruisce la lista dei timer
      this.timers = [...this.slicedTimers[0], ...arr];

      this.postTimers();
    },

applyTemplate() {
  // Se l'ID selezionato è lo stesso di quello iniziale automatico, ricarica i dati reali da JW
  if (this.initialTemplateId && Number(this.selectedTemplateId) === Number(this.initialTemplateId)) {
    fetch("api/meeting")
      .then((res) => res.json())
      .then((data) => {
        if (data) {
          this.conferenceStart = stringToDate(data?.conferenceStart);
          this.conferenceEnd = stringToDate(data?.conferenceEnd);
          this.timers = data?.timers.map((timer) => this.timerMapper(timer));
          this.startCountdown();
        }
      })
      .catch((err) => console.error("Errore nel ripristino dei dati automatici JW:", err));
    return;
  }

  // Altrimenti, per tutti gli altri template, usa il comportamento statico standard
  const templateToApply = this.templates.find((template) => {
    return template.id === Number(this.selectedTemplateId);
  });
  
  if (templateToApply) {
    this.conferenceStart = stringToDate(templateToApply.conferenceStart);
    this.conferenceEnd = stringToDate(templateToApply.conferenceEnd);
    this.timers = templateToApply.timers.map((timer) =>
      this.timerMapper(timer)
    );
  }
},

    timerMapper(timer) {
      const startDate = stringToDate(timer.start);
      const endDate = timer.end
        ? stringToDate(timer.end)
        : new Date(startDate.getTime() + timer.maxDuration * 1000);
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

    startCountdown(start = undefined, end = undefined, duration = undefined) {
      if (
        !!this.countdownTimeout &&
        (!!this.isTimerActive || !!this.conferenceStart)
      ) {
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

        this.barValue = Math.max(
          Math.floor(
            ((Number(this.mins) * 60 + Number(this.secs)) * 100) / duration
          ),
          1
        );
      } else {
        this.barValue = 0;
        this.showBar = !this.showBar;
        this.delay = true;
        diff = Math.abs(diff);
        this.mins = String(Math.floor(diff / 60)).padStart(2, "0");
        this.secs = String(diff % 60).padStart(2, "0");
      }

      this.countdownTimeout = setTimeout(
        () => this.updateCountdown(end, duration),
        1000
      );
    },

    deleteTimer(timer) {
      this.timers = this.timers.filter((item) => item.id !== timer.id);
    },

    setEndAuto() {
      const startDate = this.conferenceStart;

      const endTimestamp =
        startDate.getTime() +
        this.timers.map((timer) => timer.duration).reduce((a, b) => a + b, 0) *
          1000;

      const endDate = new Date(endTimestamp);
      this.conferenceEnd = endDate;
    },

    setStartAuto() {
      const endDate = this.conferenceEnd;

      const startTimpestamp =
        endDate.getTime() -
        this.timers.map((timer) => timer.duration).reduce((a, b) => a + b, 0) *
          1000;

      const startDate = new Date(startTimpestamp);
      this.conferenceStart = startDate;
    },

    get isTimerActive() {
      return this.timers?.some((timer) => timer.active);
    },

    get activeTimer() {
      return this.timers?.find((timer) => timer.active);
    },

    next() {
      if (this.isTimerActive) {
        const activeTimer = this.timers.indexOf(
          this.timers.find((timer) => timer.active)
        );
        const nextTimer =
          this.timers.length > activeTimer + 1 ? activeTimer + 1 : undefined;
        this.timers[activeTimer].active = false;
        if (nextTimer !== undefined) {
          this.timers[activeTimer].end = new Date();
          this.timers[nextTimer].active = true;
          this.timers[nextTimer].start = new Date();
        }
      } else {
        if (this.timers.length > 0) {
          this.timers[0].active = true;
          this.timers[0].start = new Date();
        }
      }
    },

    back() {
      if (this.isTimerActive) {
        const activeTimer = this.timers.indexOf(
          this.timers.find((timer) => timer.active)
        );
        const prevTimer = activeTimer > 0 ? activeTimer - 1 : undefined;
        this.timers[activeTimer].active = false;
        if (prevTimer !== undefined) {
          this.timers[prevTimer].active = true;
          this.timers[prevTimer].start = new Date();
        }
      } else return;
    },

    get slicedTimers() {
      if (!!this.timers) {
        const index = this.timers.findIndex((item) => item.active === true);

        if (index === -1) return [[], this.timers];

        return [this.timers.slice(0, index), this.timers.slice(index)];
      }
      return [[], []];
    },

    refreshTimerQueue() {
      if (!this.isTimerActive) {
        let currentTime = this.conferenceStart;
        this.timers = this.timers.map((timer) => {
          const start = new Date(currentTime);
          const end = new Date(start.getTime() + timer.duration * 1000);
          currentTime = new Date(end);
          return { ...timer, start, end };
        });
      } else {
        [past, forward] = this.slicedTimers;
        let currentTime = forward[0]?.start;
        forward = forward.map((timer) => {
          const start = new Date(currentTime);
          const end = new Date(start.getTime() + timer.duration * 1000);
          currentTime = new Date(end);
          return { ...timer, start, end };
        });
        this.timers = [...past, ...forward];
      }
    },

    postTimers() {
      this.refreshTimerQueue();
      pastTimers = this.slicedTimers[0].map((timer) => {
        return {
          id: timer.id,
          name: timer.name,
          start: timer.start?.toTimeString().slice(0, 8),
          end: timer.end?.toTimeString().slice(0, 8),
          active: timer.active,
          duration: Math.floor(
            (timer.end.getTime() - timer.start.getTime()) / 1000
          ),
          maxDuration: timer.maxDuration,
        };
      });

      forwardTimers = this.slicedTimers[1].map((timer) => {
        return {
          id: timer.id,
          name: timer.name,
          start: timer.start?.toTimeString().slice(0, 8),
          end: undefined,
          active: timer.active,
          duration: undefined,
          maxDuration: timer.maxDuration,
        };
      });

      fetch("/api/meeting", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          id: this.selectedTemplateId,
          conferenceStart: this.conferenceStart.toTimeString().slice(0, 8),
          conferenceEnd: this.conferenceEnd.toTimeString().slice(0, 8),
          timers:
            this.slicedTimers[0].length > 0 && this.slicedTimers[1].length > 0
              ? pastTimers.concat(forwardTimers)
              : this.slicedTimers[0].length > 0
              ? pastTimers
              : this.slicedTimers[1].length > 0
              ? forwardTimers
              : [],
        }),
      });
    },

    getSecondsString(seconds) {
      return (
        Math.floor(seconds / 60)
          .toString()
          .padStart(2, "0") +
        ":" +
        (seconds % 60).toString().padStart(2, "0")
      );
    },
  }));
});

function enforceMinMax(el) {
  if (el.value != "") {
    if (parseInt(el.value) < parseInt(el.min)) {
      el.value = el.min;
    }
    if (parseInt(el.value) > parseInt(el.max)) {
      el.value = el.max;
    }
  }
}

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
