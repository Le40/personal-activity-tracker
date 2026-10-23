// PATRICK UI: one Vue component, no build tools or frontend router.
// API
const ACTIVITIES_URL = "/activities";

// USER SETTINGS
const AUTOSAVE_DELAY_MS = 5000;         // Autosave after 5 seconds
const REPORTING_DAY_START_HOUR = 5;     // New day starts at 05:00
const DEFAULT_ACTIVITY_TYPE = "work";   // Initially selected activity type

const NOTES_PREVIEW_CHARS = 25;         // Characters from notes shown in history
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
            collapsedBeforeForm: false,
            activeActivity: null,
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
            confirmMessage: "",
        };
    },

    computed: {
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
        history() {
            this.$nextTick(() => {
                const list = document.getElementById("activities");
                if (list) {
                    list.scrollTop = list.scrollHeight;
                }
            });
        },

        formCollapsed(collapsed) {
            document.getElementById("app")
                .classList.toggle("form-collapsed", collapsed);
        }
    },

    methods: {
        formatTime,
        formatDuration,

        typeLabel(type) {
            return this.activityOptions.find(item => item.value === type)?.label ?? type;
        },
        displayName(activity) {
            const name = activity.name?.trim();

            if (name) return name;

            const notes = activity.notes?.trim();

            if (notes) {
                return notes.length > NOTES_PREVIEW_CHARS
                    ? `${notes.slice(0, NOTES_PREVIEW_CHARS)}…`
                    : notes;
            }

            return "";
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
                started_at: activity.ended_at ? localDatetimeValue(activity.started_at) : "",
                ended_at: activity.ended_at ? localDatetimeValue(activity.ended_at) : ""
            } : emptyForm(type);
            this.formDirty = false;
            this.setStatus(this.formMode === "current" && this.activeActivity ? "● Saved" : "",
                           this.formMode === "current" && this.activeActivity ? "saved" : "");
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
            this.setStatus("● Unsaved changes", "unsaved");
            if (this.formMode !== "current") return;
            clearTimeout(this.autosaveTimer);
            this.autosaveTimer = setTimeout(() => {
                this.autosaveTimer = null;
                this.runAction(() => this.saveCurrent());
            }, AUTOSAVE_DELAY_MS);
        },
        formData() {
            return {
                name: this.form.name.trim() || null,
                activity_type: this.form.activity_type,
                notes: this.form.notes.trim() || null,
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
        async changeMode(mode, activity = null) {
            if (this.busy) return;
            if (mode === this.formMode && (mode !== "edit" || activity?.id === this.editingActivity?.id)) return;
            if (this.formMode === "edit" && this.formDirty) {
                if (!await this.confirmAction("Discard unsaved changes?")) return;
            }
            if (this.formMode === "current" && this.activeActivity && this.formDirty) {
                if (!await this.runAction(() => this.saveCurrent())) return;
            }
            clearTimeout(this.autosaveTimer);
            // Remember the browsing state when opening Add or Edit.
            if (this.formMode === "current" && mode !== "current") {
                this.collapsedBeforeForm = this.formCollapsed;
            }

            // Expand when opening a form, restore when returning.
            this.formCollapsed = mode === "current"
                ? this.collapsedBeforeForm
                : false;

            this.formMode = mode;
            this.editingActivity = mode === "edit" ? activity : null;
            this.populateForm(mode === "edit" ? activity : mode === "current" ? this.activeActivity : null);
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
            this.setStatus("Saving...");
            await apiRequest(`${ACTIVITIES_URL}/${this.activeActivity.id}`,
                             jsonOptions("PUT", this.formData()));
        },
        async startActivity() {
            await this.runAction(async () => {
                await apiRequest(`${ACTIVITIES_URL}/start`, jsonOptions("POST", this.formData()));
            });
        },
        async saveActivity() {
            if (this.formMode === "current") {
                await this.runAction(() => this.saveCurrent());
                return;
            }
            await this.runAction(async () => {
                const data = { ...this.formData(), ...this.completedTimestamps() };
                const url = this.formMode === "edit"
                    ? `${ACTIVITIES_URL}/${this.editingActivity.id}` : ACTIVITIES_URL;
                const method = this.formMode === "edit" ? "PUT" : "POST";
                await apiRequest(url, jsonOptions(method, data));
                this.formMode = "current";
                this.editingActivity = null;
                this.formCollapsed = this.collapsedBeforeForm;
            });
        },
        async stopActivity() {
            await this.runAction(async () => {
                if (this.formDirty) await this.saveCurrent();
                await apiRequest(`${ACTIVITIES_URL}/stop`, { method: "POST" });
            });
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
                this.formMode = "current";
                this.editingActivity = null;
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
        try {
            await this.loadOptions();
            await this.loadActivities();
            this.populateForm(this.activeActivity);
        } catch (error) {
            this.setStatus(error.message, "error");
        }
    },
    beforeUnmount() {
        clearInterval(this.clockTimer);
        clearTimeout(this.autosaveTimer);
    }
}).mount("#app");
