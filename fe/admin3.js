document.addEventListener("alpine:init", () => {
  const { getClockObj, getEndMeetingGreeting, secondsToMinutesString, stringToDate } = window.TimerAppUtils;

  Alpine.data("admin", () => ({
    min: 1,
    max: 45,
    modalIsOpen: false,
    movingId: null,

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

    endDate: new Date(),
    eventSource: new EventSource("/stream"),
    delay: false,
    countdownTimeout: undefined,
    loading: false,
    
    // Flag e timeout di blocco per prevenire il rimbalzo asincrono
    isUpdatingLocal: false,
    lockTimeout: null,
    
    // Nuova proprietà sincronizzata
    endMeetingMode: false,
    remoteUrl: '',
    copied: false,

    warningMessage: '',
    clock: { hm: "", s: "" },

    init() {
      console.log("v. 0.0.6 ~ Giuseppe Di Menna 2026");
      this.initClock();
      
      this.$watch("selectedTemplateId", (value, oldValue) => {
        if (oldValue !== undefined && value !== oldValue) {
          this.applyTemplate();
        }
      });

      this.$watch("conferenceStart", (value, oldValue) => {
        if (value?.toTimeString().slice(0, 5) !== oldValue?.toTimeString().slice(0, 5)) {
          this.startCountdown();
        }
      this.getRemoteBase();
      });

      // 1. Carica prima i template disponibili per la select
      fetch("/api/templates")
        .then((res) => res.json())
        .then((data) => {
          this.templates = data;
        })
        .then(() => {
          // 2. Chiedi DIRETTAMENTE lo stato corrente del meeting
          fetch("api/meeting")
            .then((res) => res.json())
            .then((data) => {
              if (data) {
                this.conferenceStart = stringToDate(data?.conferenceStart);
                this.conferenceEnd = stringToDate(data?.conferenceEnd);
                this.endMeetingMode = !!data?.endMeetingMode;
                this.timers = data?.timers.map((timer) => this.timerMapper(timer));
                
                if (data.id) {
                  this.selectedTemplateId = data.id;
                }
                
                this.startCountdown();
              }
            });
        });

      // Ascolto in tempo reale dei cambi fatti dagli altri dispositivi
      this.eventSource.addEventListener("message", (e) => {
        // Se c'è un blocco locale attivo, scarta a priori qualsiasi dato dal server
        if (this.isUpdatingLocal) {
          return;
        }

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

    apriFinestraClient() {
      window.open('/', '_blank', 'popup=yes,width=1200,height=800');
    },

    toggleEndMeeting() {
      this.endMeetingMode = !this.endMeetingMode;
      this.postTimers();
    },

    initClock() {
      this.clock = getClockObj();
      setInterval(() => {
        this.clock = getClockObj();
      }, 1000);
    },

    getEndMeetingGreeting() {
      return getEndMeetingGreeting(this.clock);
    },

    clearWarning() {
      this.warningMessage = "";
    },

    startPreviousTimer() {
      this.back();
      this.startCountdown();
    },

    startNextTimer() {
      this.next();
      this.startCountdown();
    },

    updateConferenceStart() {
      this.setEndAuto();
      this.postTimers();
    },

    updateConferenceEnd() {
      this.setStartAuto();
      this.postTimers();
    },

    deleteAndPost(timer) {
      this.deleteTimer(timer);
      this.postTimers();
    },

    openAddTimerModal() {
      this.modalIsOpen = true;
    },

    closeAddTimerModal() {
      this.modalIsOpen = false;
    },

    confirmAddTimer() {
      this.closeAddTimerModal();
      this.addTimer();
    },

    decrementInsertingDuration() {
      this.insertingDuration = Math.max(this.min, this.insertingDuration - 1);
    },

    incrementInsertingDuration() {
      this.insertingDuration = Math.min(this.max, this.insertingDuration + 1);
    },

    decrementTimerDuration(timer) {
      timer.maxDuration = Math.max(60, timer.maxDuration - 60);
      timer.duration = timer.maxDuration;
      this.postTimers();
    },

    incrementTimerDuration(timer) {
      timer.maxDuration += 60;
      timer.duration = timer.maxDuration;
      this.postTimers();
    },

    addTimer() {
      const durataNuovaParteSecondi = this.insertingDuration * 60;

      this.timers.push({
        id: Math.max.apply(Math, this.timers.map((timer) => timer.id)) + 1,
        duration: durataNuovaParteSecondi,
        maxDuration: durataNuovaParteSecondi,
        name: this.insertingName,
        active: false,
      });
      this.insertingDuration = 10;
      this.insertingName = "Parte";
      this.postTimers();
    },

    getRemoteBase() {
      fetch("/api/network-info")
        .then((res) => res.json())
        .then((data) => {
          this.remoteUrl = `http://${data.ip}:${data.port}/`;
        });
    },
    
    copyLink(url) {
      navigator.clipboard.writeText(url).then(() => {
        this.copied = true;
        clearTimeout(this._copiedTimeout);
        this._copiedTimeout = setTimeout(() => (this.copied = false), 1500);
      });
    },
  
    showWarning(msg) {
      this.warningMessage = msg;
      clearTimeout(this._warningTimeout);
      this._warningTimeout = setTimeout(() => (this.warningMessage = ''), 4000);
    },
    get calculatedEnd() {
      if (!this.isTimerActive) return "";

      const forward = this.slicedTimers[1];
      if (forward.length > 0) {
        const start = forward[0].start;
        return new Date(start.getTime() + forward.map((timer) => timer.duration).reduce((a, b) => a + b, 0) * 1000).toTimeString().slice(0, 5);
      }
      return this.conferenceEnd?.toTimeString().slice(0, 5);
    },

    get meetingInDelay() {
      const calculatedEnd = stringToDate(this.calculatedEnd).getTime();
      return this.conferenceEnd.getTime() < calculatedEnd;
    },

    get effectiveStart() {
      return this.isTimerActive ? this.timers[0]?.start?.toTimeString().slice(0, 5) : "";
    },

    // Gestore dell'animazione dello scambio prima del riordinamento dell'array
    animateMove(index, direction) {
      const forward = this.slicedTimers[1];
      const currentTimer = forward[index];
      if (!currentTimer) return;

      // Salva l'ID del timer che si sta muovendo per applicargli la classe di "sollevamento"
      this.movingId = currentTimer.id;

      // Esegui lo spostamento logico effettivo
      if (direction === 'up') {
        this.moveUp(index);
      } else {
        this.moveDown(index);
      }

      // Rimuovi lo stato di movimento dopo che la transizione CSS è finita (300ms)
      setTimeout(() => {
        this.movingId = null;
      }, 300);
    },

    // Sposta in su nella coda dei timer modificabili (forward) con i vecchi fix inclusi
    moveUp(index) {
      if (index <= 0) return;
      if (index === 1 && this.isTimerActive) return; 
      
      let forward = [...this.slicedTimers[1]];
      let temp = forward[index];
      forward[index] = forward[index - 1];
      forward[index - 1] = temp;
      
      this.timers = [...this.slicedTimers[0], ...forward];
      this.postTimers();
    },

    // Sposta in giù nella coda dei timer modificabili (forward)
    moveDown(index) {
      let forward = [...this.slicedTimers[1]];
      if (index >= forward.length - 1) return;
      if (index === 0 && this.isTimerActive) return; 
      
      let temp = forward[index];
      forward[index] = forward[index + 1];
      forward[index + 1] = temp;
      
      this.timers = [...this.slicedTimers[0], ...forward];
      this.postTimers();
    },

    applyTemplate() {
      const templateToApply = this.templates.find((t) => t.id === Number(this.selectedTemplateId));
      if (templateToApply) {
        this.conferenceStart = stringToDate(templateToApply.conferenceStart);
        this.conferenceEnd = stringToDate(templateToApply.conferenceEnd);
        this.timers = templateToApply.timers.map((timer) => this.timerMapper(timer));
      }
    },

    saveTemplateStart() {
      if (!this.selectedTemplateId) return;

      this.postTimers()
        .then(() => fetch("/api/templates"))
        .then((res) => res.json())
        .then((data) => {
          this.templates = data;
        })
        .catch((err) => console.error("Errore nel ricaricare i template:", err));
    },

    timerMapper(timer) {
      const startDate = stringToDate(timer.start);
      const endDate = timer.end ? stringToDate(timer.end) : new Date(startDate.getTime() + timer.maxDuration * 1000);
      return {
        id: timer.id,
        duration: timer.duration ?? timer.maxDuration,
        maxDuration: timer.maxDuration,
        name: timer.name,
        active: timer.active,
        start: startDate,
        end: endDate,
      };
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
        this.barValue = Math.max(Math.floor(((Number(this.mins) * 60 + Number(this.secs)) * 100) / duration), 1);
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

    deleteTimer(timer) {
      this.timers = this.timers.filter((item) => item.id !== timer.id);
    },

    setEndAuto() {
      const startDate = this.conferenceStart;
      const durataTotaleSecondi = this.timers.map((t) => t.duration).reduce((a, b) => a + b, 0);
      const endTimestamp = startDate.getTime() + durataTotaleSecondi * 1000;
      this.conferenceEnd = new Date(endTimestamp);
    },

    setStartAuto() {
      const endDate = this.conferenceEnd;
      const durataTotaleSecondi = this.timers.map((t) => t.duration).reduce((a, b) => a + b, 0);
      const startTimpestamp = endDate.getTime() - durataTotaleSecondi * 1000;
      this.conferenceStart = new Date(startTimpestamp);
    },

    get isTimerActive() {
      return this.timers?.some((timer) => timer.active);
    },
    get activeTimer() {
      return this.timers?.find((timer) => timer.active);
    },

    next() {
      if (this.isTimerActive) {
        const activeTimer = this.timers.indexOf(this.timers.find((timer) => timer.active));
        const nextTimer = this.timers.length > activeTimer + 1 ? activeTimer + 1 : undefined;
      
        const current = this.timers[activeTimer];
        current.active = false;
        current.end = new Date();
      
        // Salva e blocca i secondi effettivi passati
        const secondiEffettivi = Math.floor((current.end.getTime() - current.start.getTime()) / 1000);
        current.duration = Math.max(1, secondiEffettivi); 
      
        if (nextTimer !== undefined) {
          this.timers[nextTimer].active = true;
          this.timers[nextTimer].start = new Date();
          this.timers[nextTimer].end = undefined;
          this.timers[nextTimer].duration = this.timers[nextTimer].maxDuration;
        }
      
        this.postTimers();
      } else {
        if (this.timers.length > 0) {
          this.timers[0].active = true;
          this.timers[0].start = new Date();
          this.timers[0].end = undefined;
          this.timers[0].duration = this.timers[0].maxDuration;
          this.postTimers();
        }
      }
    },

    back() {
      if (this.isTimerActive) {
        const activeTimer = this.timers.indexOf(this.timers.find((timer) => timer.active));
        const prevTimer = activeTimer > 0 ? activeTimer - 1 : undefined;
      
        if (prevTimer !== undefined) {
          const current = this.timers[activeTimer];
          current.active = false;
          current.end = undefined;
          // Ritornando indietro, la parte che abbandoni torna ad avere la sua durata nominale
          current.duration = current.maxDuration; 
        
          const prev = this.timers[prevTimer];
          prev.active = true;
          prev.end = undefined;
          prev.duration = prev.maxDuration; 
        
          this.postTimers();
        } else {
          const current = this.timers[activeTimer];
          current.active = false;
          current.end = undefined;
          current.duration = current.maxDuration;

          this.postTimers();
        }
      }
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
          const nominalDuration = timer.maxDuration ?? timer.duration;
          const end = new Date(start.getTime() + nominalDuration * 1000);
          currentTime = new Date(end);
          return { ...timer, duration: nominalDuration, start, end };
        });
      } else {
        const [past, forward] = this.slicedTimers;
        let currentTime = forward[0]?.start;
        const mappedForward = forward.map((timer) => {
          const start = new Date(currentTime);
          const end = new Date(start.getTime() + timer.duration * 1000);
          currentTime = new Date(end);
          return { ...timer, start, end };
        });
        this.timers = [...past, ...mappedForward];
      }
    },

    postTimers() {
      this.refreshTimerQueue();

      this.isUpdatingLocal = true;
      if (this.lockTimeout) clearTimeout(this.lockTimeout);

      this.lockTimeout = setTimeout(() => {
        this.isUpdatingLocal = false;
      }, 2000);
    
      const pastTimers = this.slicedTimers[0].map((timer) => {
        return {
          id: timer.id,
          name: timer.name,
          start: timer.start?.toTimeString().slice(0, 8),
          end: timer.end?.toTimeString().slice(0, 8),
          active: timer.active,
          // Mantiene rigorosamente la durata reale calcolata al momento del cambio
          duration: timer.duration, 
          maxDuration: timer.maxDuration,
        };
      });

      const forwardTimers = this.slicedTimers[1].map((timer) => {
        return {
          id: timer.id,
          name: timer.name,
          start: timer.start?.toTimeString().slice(0, 8),
          end: timer.end ? timer.end.toTimeString().slice(0, 8) : undefined, 
          active: timer.active,
          // Se è attivo usa la sua duration corrente, altrimenti usa maxDuration
          duration: timer.active ? timer.duration : timer.maxDuration, 
          maxDuration: timer.maxDuration,
        };
      });
    
      return fetch("/api/meeting", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id: this.selectedTemplateId,
          conferenceStart: this.conferenceStart.toTimeString().slice(0, 8),
          conferenceEnd: this.conferenceEnd.toTimeString().slice(0, 8),
          endMeetingMode: this.endMeetingMode,
          timers: this.slicedTimers[0].length > 0 && this.slicedTimers[1].length > 0
              ? pastTimers.concat(forwardTimers)
              : this.slicedTimers[0].length > 0
              ? pastTimers
              : this.slicedTimers[1].length > 0
              ? forwardTimers
              : [],
        }),
      })
        .then((res) => res.json())
        .then((refreshed) => {
          if (!refreshed?.timers?.length) return;
          this.timers = this.timers.map((timer) => {
            if (timer.active) return timer;
            const serverTimer = refreshed.timers.find((t) => t.id === timer.id);
            return serverTimer ? this.mergeServerTimer(timer, serverTimer) : timer;
          });
        })
        .catch((err) => console.error("Errore postTimers:", err));
    },

    mergeServerTimer(localTimer, serverTimer) {
      return {
        ...localTimer,
        duration: serverTimer.duration,
        maxDuration: serverTimer.maxDuration,
        start: stringToDate(serverTimer.start),
        end: serverTimer.end ? stringToDate(serverTimer.end) : localTimer.end,
      };
    },

    getSecondsString(seconds) {
      return secondsToMinutesString(seconds);
    },
  }));
});

// Le funzioni globali di utilità rimangono invariate
function enforceMinMax(el) {
  if (el.value != "") {
    if (parseInt(el.value) < parseInt(el.min)) el.value = el.min;
    if (parseInt(el.value) > parseInt(el.max)) el.value = el.max;
  }
}
