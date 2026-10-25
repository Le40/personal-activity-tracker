// PATRICK UI: one Vue component, no build tools or frontend router.
// API
const ACTIVITIES_URL = "/activities";

// USER SETTINGS
const AUTOSAVE_DELAY_MS = 5000;         // Autosave after 5 seconds
const REPORTING_DAY_START_HOUR = 5;     // New day starts at 05:00
const DEFAULT_ACTIVITY_TYPE = "work";   // Initially selected activity type

const MIN_GAP_MINUTES = 5;              // Minimum gap suggested for past activities
const GAP_LOOKBACK_DAYS = 2;            // Additional days searched for available gaps
const DEFAULT_PAST_DURATION_MINUTES = 60;


// TIME HELPERS — backend timestamps without offsets are UTC.
function parseTimestamp(timestamp) {
    const hasTimezone = /(?:Z|[+-]\d{2}:\d{2})$/i.test(timestamp);
    return new Date(hasTimezone ? timestamp : `${timestamp}Z`);
}

function formatTime(timestamp) {
    return parseTimestamp(timestamp).toLocaleTimeString("sk-SK", {
        hour: "2-digit", minute: "2-digit"
    });
}

function formatDuration(startedAt, endedAt) {
    const minutes = Math.max(0, Math.floor(
        (parseTimestamp(endedAt) - parseTimestamp(startedAt)) / 60000
    ));
    const hours = Math.floor(minutes / 60);
    return hours
        ? `${hours}h ${String(minutes % 60).padStart(2, "0")}m`
        : `${minutes}m`;
}

function localDatetimeValue(timestamp) {
    const date = timestamp instanceof Date ? timestamp : parseTimestamp(timestamp);
    const pad = number => String(number).padStart(2, "0");
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
           `T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function reportingDay() {
    const date = new Date();
    if (date.getHours() < REPORTING_DAY_START_HOUR) date.setDate(date.getDate() - 1);
    const pad = number => String(number).padStart(2, "0");
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function localDateString(date) {
    const pad = number => String(number).padStart(2, "0");

    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function usableGap(start, end) {
    if (!start) return null;

    // The form supports minute precision.
    // Round inward to avoid overlapping existing activities.
    const minute = 60_000;

    const roundedStart = new Date(
        Math.ceil(start.getTime() / minute) * minute
    );

    const roundedEnd = new Date(
        Math.floor(end.getTime() / minute) * minute
    );

    if (roundedEnd - roundedStart < MIN_GAP_MINUTES * minute) {
        return null;
    }
    return {
        start: roundedStart,
        end: roundedEnd
    };
}

function emptyForm(activityType = DEFAULT_ACTIVITY_TYPE) {
    return {
        name: "", activity_type: activityType, notes: "", ease_rating: "",
        started_at: "", ended_at: ""
    };
}

// API — all endpoints return JSON, except successful 204 responses.
async function apiRequest(url, options = {}) {
    const response = await fetch(url, options);
    if (!response.ok) {
        let message = `Request failed: HTTP ${response.status}`;
        try {
            const error = await response.json();
            if (typeof error.detail === "string") message = error.detail;
            else if (Array.isArray(error.detail)) {
                message = error.detail.map(item => item.msg).join("; ");
            }
        } catch { /* Keep HTTP status when response has no JSON body. */ }
        throw new Error(message);
    }
    return response.status === 204 ? null : response.json();
}

function jsonOptions(method, data) {
    return {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
    };
}

Vue.createApp({
    data() {
        return {
            formMode: "current", // current | add | edit
            form: emptyForm(),
            formCollapsed: false,
            runningCollapsed: false, // Restore this when returning from Past/Edit
            activeActivity: null,
            pendingRatingActivity: null, // Recently stopped Work activity awaiting rating
            editingActivity: null,
            history: [],
            historyDate: reportingDay(),
            activityOptions: [],
            easeRatings: [],
            busy: false,
            formDirty: false,
            statusMessage: "",
            statusState: "",
            now: Date.now(),
            autosaveTimer: null,
            clockTimer: null,
            modeHeightAnimation: null,
            historyResizeObserver: null,
            confirmMessage: "",
        };
    },

    computed: {
        currentView() {
            if (this.pendingRatingActivity) return "rating";
            return this.activeActivity ? "running" : "ready";
        },
        currentTabLabel() {
            const activity = this.pendingRatingActivity ?? this.activeActivity;
            if (!activity) return "Current activity";
            const name = activity.name?.trim() || this.typeLabel(activity.activity_type);
            return this.activeActivity
                ? `${name} | ${this.typeLabel(activity.activity_type)} | ${this.timerText}`
                : `${name} | ${this.typeLabel(activity.activity_type)}`;
        },
        isEditingRunning() {
            return this.formMode === "edit" && this.editingActivity?.ended_at == null;
        },
        visibleHistory() {
            // The current session belongs only to the currently selected reporting day.
            if (!this.activeActivity || this.historyDate !== reportingDay()) return this.history;
            return [...this.history, this.activeActivity].sort(
                (a, b) => parseTimestamp(a.started_at) - parseTimestamp(b.started_at)
            );
        },
        runningStatusText() {
            if (this.statusMessage === "● Unsaved changes") return "● Unsaved";
            return this.statusMessage;
        },
        heading() {
            if (this.formMode === "edit") return "Edit Activity";
            if (this.formMode === "add") return "Add Past Activity";
            return this.activeActivity ? "Current Activity" : "New Activity";
        },
        supportsRating() {
            const selected = this.activityOptions.find(
                item => item.value === this.form.activity_type
            );
            return selected?.supports_ease_rating === true;
        },
        timerText() {
            if (!this.activeActivity) return "00:00:00";
            const seconds = Math.max(0, Math.floor(
                (this.now - parseTimestamp(this.activeActivity.started_at)) / 1000
            ));
            const pad = number => String(number).padStart(2, "0");
            return `${pad(Math.floor(seconds / 3600))}:` +
                   `${pad(Math.floor((seconds % 3600) / 60))}:` +
                   `${pad(seconds % 60)}`;
        }
    },

    watch: {
        visibleHistory() {
            // Keep the latest entry in view when records are added or replaced.
            this.$nextTick(() => this.scrollHistoryToBottom());
        },

        formCollapsed(collapsed) {
            document.getElementById("app")
                .classList.toggle("form-collapsed", collapsed);
        }
    },

    methods: {
        formatTime,
        formatDuration,

        scrollHistoryToBottom() {
            const list = document.getElementById("activities");
            if (list) list.scrollTop = list.scrollHeight;
        },

        typeLabel(type) {
            return this.activityOptions.find(item => item.value === type)?.label ?? type;
        },
        displayName(activity) {
            const name = activity.name?.trim();

            if (name) return name;

            const notes = activity.notes?.trim();
            // Show only the first line, and let CSS truncate to the available width.
            return notes ? notes.split(/\r?\n/, 1)[0] : "";
        },
        historyTooltip(activity) {
            // Native title tooltips preserve newlines in the full notes.
            return activity.notes?.trim() || this.displayName(activity);
        },
        datetimeLabel(value) {
            if (!value) return "dd.mm.yyyy --:--";
            const [date, time] = value.split("T");
            const [year, month, day] = date.split("-");
            return `${day}.${month}.${year} ${time.slice(0, 5)}`;
        },
        openDatePicker(event) {
            try { event.target.showPicker?.(); } catch { /* Picker availability is browser-dependent. */ }
        },
        setStatus(message, state = "") {
            this.statusMessage = message;
            this.statusState = state;
        },
        populateForm(activity = null) {
            const type = DEFAULT_ACTIVITY_TYPE;
            this.form = activity ? {
                name: activity.name ?? "",
                activity_type: activity.activity_type,
                notes: activity.notes ?? "",
                ease_rating: activity.ease_rating == null ? "" : String(activity.ease_rating),
                started_at: localDatetimeValue(activity.started_at),
                ended_at: activity.ended_at ? localDatetimeValue(activity.ended_at) : ""
            } : emptyForm(type);
            this.formDirty = false;
            this.setStatus("");
        },
        onTypeChanged() {
            if (!this.supportsRating) this.form.ease_rating = "";
            this.markUnsaved();
        },
        markUnsaved() {
            if (this.busy) return;
            // Before an activity starts, values are a draft, not an unsaved DB record.
            if (this.formMode === "current" && !this.activeActivity) return;
            this.formDirty = true;
            // Normal autosave is silent. Only failures need a status message.
            this.setStatus("");
            if (this.formMode !== "current") return;
            clearTimeout(this.autosaveTimer);
            this.autosaveTimer = setTimeout(() => {
                this.autosaveTimer = null;
                this.runAction(() => this.saveCurrent());
            }, AUTOSAVE_DELAY_MS);
        },
        formData() {
            // Editing a running activity hides Notes. Preserve autosaved notes
            // instead of replacing them with the form's hidden/stale value.
            const notes = this.isEditingRunning
                ? this.editingActivity.notes
                : this.form.notes.trim() || null;
            return {
                name: this.form.name.trim() || null,
                activity_type: this.form.activity_type,
                notes,
                ease_rating: this.supportsRating && this.form.ease_rating !== ""
                    ? Number(this.form.ease_rating) : null
            };
        },
        completedTimestamps() {
            if (!this.form.started_at || !this.form.ended_at) {
                throw new Error("Enter both start and end times.");
            }
            let startedAt = new Date(this.form.started_at);
            let endedAt = new Date(this.form.ended_at);

            // Editing unchanged minute-level inputs must preserve original seconds.
            if (this.formMode === "edit" && this.editingActivity) {
                if (this.form.started_at === localDatetimeValue(this.editingActivity.started_at)) {
                    startedAt = parseTimestamp(this.editingActivity.started_at);
                }
                if (this.form.ended_at === localDatetimeValue(this.editingActivity.ended_at)) {
                    endedAt = parseTimestamp(this.editingActivity.ended_at);
                }
            }
            if (!Number.isFinite(startedAt.getTime()) || !Number.isFinite(endedAt.getTime())) {
                throw new Error("Invalid date or time.");
            }
            if (endedAt <= startedAt) throw new Error("End time must be after start time.");
            if (startedAt > new Date() || endedAt > new Date()) {
                throw new Error("Activity times cannot be in the future.");
            }
            return { started_at: startedAt.toISOString(), ended_at: endedAt.toISOString() };
        },
        confirmAction(message) {
            this.confirmMessage = message;

            const dialog = this.$refs.confirmDialog;
            dialog.returnValue = "cancel";

            return new Promise(resolve => {
                dialog.addEventListener("close", () => {
                    resolve(dialog.returnValue === "confirm");
                }, { once: true });

                dialog.showModal();
            });
        },
        async loadOptions() {
            const options = await apiRequest(`${ACTIVITIES_URL}/options`);
            this.activityOptions = options.activity_types;
            this.easeRatings = options.ease_ratings;
        },
        async loadHistory() {
            const day = this.historyDate;

            const query = new URLSearchParams({
                start_date: day,
                end_date: day
            });

            const completed = await apiRequest(`${ACTIVITIES_URL}?${query}`);

            // Ignore an outdated response if the user selected another date.
            if (day !== this.historyDate) return;

            this.history = completed.sort(
                (a, b) => parseTimestamp(a.started_at) - parseTimestamp(b.started_at)
            );
        },

        async loadActivities() {
            const [current] = await Promise.all([
                apiRequest(`${ACTIVITIES_URL}/current`),
                this.loadHistory()
            ]);

            this.activeActivity = current;
        },

        async onHistoryDateChange() {
            // Browsing the history also dismisses a pending rating.
            if (this.pendingRatingActivity) this.skipRating();
            try {
                await this.loadHistory();
            } catch (error) {
                this.setStatus(error.message, "error");
            }
        },
        async runAction(action) {
            if (this.busy) return false;
            clearTimeout(this.autosaveTimer);
            this.autosaveTimer = null;
            this.busy = true;
            try {
                await action();
                await this.loadActivities();
                const selected = this.formMode === "current" ? this.activeActivity :
                                 this.formMode === "edit" ? this.editingActivity : null;
                this.populateForm(selected);
                return true;
            } catch (error) {
                this.setStatus(error.message, "error");
                return false;
            } finally {
                this.busy = false;
            }
        },
        onPastTabClick() {
            if (this.formMode === "current") {
                // First click always opens Past Activity, even if it was collapsed.
                this.changeMode("add");
            } else if (!this.busy) {
                // The same tab toggles Add and Edit forms without losing draft input.
                this.modeHeightAnimation?.cancel();
                this.modeHeightAnimation = null;
                document.querySelector(".activity-section").classList.remove("mode-height-transition");
                this.formCollapsed = !this.formCollapsed;
            }
        },
        async changeMode(mode, activity = null) {
            if (this.busy) return;
            if (mode === this.formMode && (mode !== "edit" || activity?.id === this.editingActivity?.id)) {
                if (this.pendingRatingActivity) {
                    this.skipRating();
                } else if (mode === "current" && this.activeActivity) {
                    // Only the Running view toggles by clicking its tab.
                    if (this.formDirty && !await this.runAction(() => this.saveCurrent())) return;
                    this.modeHeightAnimation?.cancel();
                    this.modeHeightAnimation = null;
                    document.querySelector(".activity-section").classList.remove("mode-height-transition");
                    this.runningCollapsed = !this.runningCollapsed;
                    this.formCollapsed = this.runningCollapsed;
                }
                return;
            }
            if ((this.formMode === "edit" || this.formMode === "add") && this.formDirty) {
                if (!await this.confirmAction("Discard unsaved changes?")) return;
            }
            if (this.formMode === "current" && this.activeActivity && this.formDirty) {
                if (!await this.runAction(() => this.saveCurrent())) return;
            }
            if (this.formMode === "current" && this.activeActivity) {
                this.runningCollapsed = this.formCollapsed;
            }
            clearTimeout(this.autosaveTimer);
            // Capture the previous height before Vue replaces the form. Without
            // this, switching from a tall Past form to collapsed Running jumps.
            const section = document.querySelector(".activity-section");
            const panel = section.querySelector(".activity-panel");
            const previousHeight = panel.getBoundingClientRect().height;
            this.modeHeightAnimation?.cancel();
            this.modeHeightAnimation = null;
            section.classList.add("mode-height-transition");

            // The rating is a one-time prompt; navigating away skips it.
            this.pendingRatingActivity = null;
            this.formMode = mode;
            this.formCollapsed = mode === "current" && this.activeActivity
                ? this.runningCollapsed : false;
            // If Notes were just autosaved, use the refreshed running record.
            const chosen = activity?.id === this.activeActivity?.id
                ? this.activeActivity : activity;
            this.editingActivity = mode === "edit" ? chosen : null;
            this.populateForm(mode === "edit" ? chosen : mode === "current" ? this.activeActivity : null);

            // Animate one continuous height change, even when the two forms
            // have different natural heights or the destination is collapsed.
            await this.$nextTick();
            const nextHeight = panel.getBoundingClientRect().height;
            if (Math.abs(previousHeight - nextHeight) < 1 ||
                    window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
                section.classList.remove("mode-height-transition");
            } else {
                const animation = panel.animate([
                    { height: `${previousHeight}px` },
                    { height: `${nextHeight}px` }
                ], { duration: 360, easing: "ease-in-out" });
                this.modeHeightAnimation = animation;
                const finish = () => {
                    if (this.modeHeightAnimation !== animation) return;
                    this.modeHeightAnimation = null;
                    section.classList.remove("mode-height-transition");
                };
                animation.addEventListener("finish", finish, { once: true });
                animation.addEventListener("cancel", finish, { once: true });
            }
            if (mode === "add") {
                try {
                    await this.suggestPastTimes();
                } catch (error) {
                    this.setStatus(error.message, "error");
                }
            }
        },
        async saveCurrent() {
            if (!this.activeActivity) return;
            await apiRequest(`${ACTIVITIES_URL}/${this.activeActivity.id}`,
                             jsonOptions("PUT", this.formData()));
        },
        async startActivity() {
            if (await this.runAction(async () => {
                await apiRequest(`${ACTIVITIES_URL}/start`, jsonOptions("POST", this.formData()));
            })) {
                this.runningCollapsed = false;
                this.formCollapsed = false;
            }
        },
        async saveActivity() {
            if (this.formMode === "current") {
                await this.runAction(() => this.saveCurrent());
                return;
            }
            await this.runAction(async () => {
                const data = this.isEditingRunning
                    ? this.formData() // Running timestamps cannot be edited until backend support exists.
                    : { ...this.formData(), ...this.completedTimestamps() };
                const url = this.formMode === "edit"
                    ? `${ACTIVITIES_URL}/${this.editingActivity.id}` : ACTIVITIES_URL;
                const method = this.formMode === "edit" ? "PUT" : "POST";
                await apiRequest(url, jsonOptions(method, data));
                this.pendingRatingActivity = null;
                this.formMode = "current";
                this.editingActivity = null;
                this.formCollapsed = Boolean(this.activeActivity && this.runningCollapsed);
            });
        },
        async stopActivity() {
            if (await this.runAction(async () => {
                if (this.formDirty) await this.saveCurrent();
                const stopped = await apiRequest(`${ACTIVITIES_URL}/stop`, { method: "POST" });
                const type = this.activityOptions.find(
                    item => item.value === stopped.activity_type
                );
                this.pendingRatingActivity = type?.supports_ease_rating ? stopped : null;
            })) {
                this.runningCollapsed = false;
                this.formCollapsed = false;
            }
        },
        async finishRating(rating) {
            if (!this.pendingRatingActivity) return;
            await this.runAction(async () => {
                const activity = this.pendingRatingActivity;
                await apiRequest(`${ACTIVITIES_URL}/${activity.id}`, jsonOptions("PUT", {
                    name: activity.name,
                    activity_type: activity.activity_type,
                    notes: activity.notes,
                    ease_rating: rating
                }));
                this.pendingRatingActivity = null;
            });
        },
        skipRating() {
            if (this.busy) return;
            this.pendingRatingActivity = null;
            this.populateForm(this.activeActivity);
        },
        async deleteActivity() {
            const activity = this.formMode === "edit" ? this.editingActivity : this.activeActivity;

            if (!activity) return;

            const label = this.displayName(activity) || this.typeLabel(activity.activity_type);

            if (!await this.confirmAction(`Delete "${label}"?`)) {
                return;
            }
            await this.runAction(async () => {
                await apiRequest(`${ACTIVITIES_URL}/${activity.id}`, { method: "DELETE" });
                this.pendingRatingActivity = null;
                this.formMode = "current";
                this.editingActivity = null;
                this.formCollapsed = this.activeActivity ? this.runningCollapsed : false;
            });
        },
        async suggestPastTimes() {
            const today = reportingDay();

            const lookback = new Date(`${today}T12:00:00`);
            lookback.setDate(lookback.getDate() - GAP_LOOKBACK_DAYS);

            const query = new URLSearchParams({
                start_date: localDateString(lookback),
                end_date: today
            });

            const completed = await apiRequest(`${ACTIVITIES_URL}?${query}`);

            completed.sort(
                (a, b) => parseTimestamp(a.started_at) - parseTimestamp(b.started_at)
            );

            const boundary = this.activeActivity
                ? parseTimestamp(this.activeActivity.started_at)
                : new Date();

            let previousEnd = null;
            let suggestion = null;

            // Find gaps between completed activities.computed: {
            for (const activity of completed) {
                const start = parseTimestamp(activity.started_at);
                const end = parseTimestamp(activity.ended_at);

                if (start >= boundary) break;

                if (previousEnd) {
                    suggestion = usableGap(previousEnd, start) ?? suggestion;
                }

                if (!previousEnd || end > previousEnd) {
                    previousEnd = end;
                }
            }

            // Check the final gap before now or the running activity.
            if (previousEnd) {
                const finalGap = usableGap(previousEnd, boundary);

                if (finalGap) {
                    if (!this.activeActivity) {
                        const defaultEnd = new Date(
                            finalGap.start.getTime() + DEFAULT_PAST_DURATION_MINUTES * 60_000
                        );

                        finalGap.end = new Date(
                            Math.min(defaultEnd.getTime(), finalGap.end.getTime())
                        );
                    }

                    suggestion = finalGap;
                }
            }
            if (this.formMode !== "add" || !suggestion) return;

            this.form.started_at = localDatetimeValue(suggestion.start);
            this.form.ended_at = localDatetimeValue(suggestion.end);
        }
    },

    async mounted() {
        this.clockTimer = setInterval(() => { this.now = Date.now(); }, 1000);

        // The History pane changes height as the form expands/collapses.
        // Keep the newest activity visible throughout that transition.
        const list = document.getElementById("activities");
        this.historyResizeObserver = new ResizeObserver(() => this.scrollHistoryToBottom());
        this.historyResizeObserver.observe(list);

        try {
            await this.loadOptions();
            await this.loadActivities();
            this.populateForm(this.activeActivity);
            await this.$nextTick();
            this.scrollHistoryToBottom();
        } catch (error) {
            this.setStatus(error.message, "error");
        }
    },
    beforeUnmount() {
        clearInterval(this.clockTimer);
        clearTimeout(this.autosaveTimer);
        this.historyResizeObserver?.disconnect();
    }
}).mount("#app");
