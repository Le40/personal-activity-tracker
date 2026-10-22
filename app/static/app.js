const ACTIVITIES_URL = "/activities";
const AUTOSAVE_DELAY_MS = 5000;
const REPORTING_DAY_START_HOUR = 5;

let activeActivity = null;
let editingActivity = null;
let formMode = "current"; // "current", "add", "edit"
let activityOptions = [];
let busy = false;
let autosaveTimer = null;
let formDirty = false;


// TIME

function parseTimestamp(timestamp) {
    const hasTimezone = /(?:Z|[+-]\d{2}:\d{2})$/i.test(timestamp);
    return new Date(hasTimezone ? timestamp : timestamp + "Z");
}

function formatTime(timestamp) {
    return parseTimestamp(timestamp).toLocaleTimeString("sk-SK", {
        hour: "2-digit",
        minute: "2-digit"
    });
}

function formatDuration(startedAt, endedAt) {
    const minutes = Math.max(
        0,
        Math.floor((parseTimestamp(endedAt) - parseTimestamp(startedAt)) / 60000)
    );
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;

    return hours > 0 ? `${hours}h ${remainingMinutes}m` : `${minutes}m`;
}

function toLocalDatetimeInput(timestamp) {
    const date = parseTimestamp(timestamp);
    const pad = value => String(value).padStart(2, "0");

    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
           `T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

// Show a fixed, compact dd.mm.yyyy HH:mm label while the browser handles
// the actual date/time picker. The real input always stores local ISO format.
function refreshDatetimeDisplay(inputId, displayId) {
    const value = document.getElementById(inputId).value;
    const display = document.getElementById(displayId);

    if (!value) {
        display.textContent = "dd.mm.yyyy --:--";
        return;
    }

    const [date, time] = value.split("T");
    const [year, month, day] = date.split("-");
    display.textContent = `${day}.${month}.${year} ${time.slice(0, 5)}`;
}

function refreshDatetimeDisplays() {
    refreshDatetimeDisplay("startedAt", "startedAtDisplay");
    refreshDatetimeDisplay("endedAt", "endedAtDisplay");
}

function readTimestamps() {
    const startValue = document.getElementById("startedAt").value;
    const endValue = document.getElementById("endedAt").value;

    if (!startValue || !endValue) {
        throw new Error("Enter both start and end times.");
    }

    let startedAt = new Date(startValue);
    let endedAt = new Date(endValue);

    // Native datetime-local inputs display minutes, not seconds. Preserve the
    // original exact times when editing other fields, so the edit does not
    // accidentally move boundaries and create false overlap conflicts.
    if (formMode === "edit" && editingActivity) {
        if (startValue === toLocalDatetimeInput(editingActivity.started_at)) {
            startedAt = parseTimestamp(editingActivity.started_at);
        }
        if (endValue === toLocalDatetimeInput(editingActivity.ended_at)) {
            endedAt = parseTimestamp(editingActivity.ended_at);
        }
    }

    if (!Number.isFinite(startedAt.getTime()) || !Number.isFinite(endedAt.getTime())) {
        throw new Error("Invalid date or time.");
    }
    if (endedAt <= startedAt) {
        throw new Error("End time must be after start time.");
    }

    return {
        started_at: startedAt.toISOString(),
        ended_at: endedAt.toISOString()
    };
}

function updateTimer() {
    if (formMode !== "current" || !activeActivity) return;

    const elapsed = Math.max(
        0,
        Math.floor((Date.now() - parseTimestamp(activeActivity.started_at)) / 1000)
    );

    const hours = Math.floor(elapsed / 3600);
    const minutes = Math.floor((elapsed % 3600) / 60);
    const seconds = elapsed % 60;
    const pad = value => String(value).padStart(2, "0");

    document.getElementById("timer").textContent =
        `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
}

function getReportingDay() {
    const date = new Date();
    if (date.getHours() < REPORTING_DAY_START_HOUR) {
        date.setDate(date.getDate() - 1);
    }

    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}


// API

async function apiRequest(url, options = {}) {
    const response = await fetch(url, options);

    if (!response.ok) {
        let message = `Request failed: HTTP ${response.status}`;
        try {
            const error = await response.json();
            if (typeof error.detail === "string") {
                message = error.detail;
            } else if (Array.isArray(error.detail)) {
                message = error.detail.map(item => item.msg).join("; ");
            }
        } catch {
            // Keep the HTTP status message if there is no JSON error body.
        }
        throw new Error(message);
    }

    if (response.status === 204) return null;
    return response.json();
}

async function loadOptions() {
    const options = await apiRequest(`${ACTIVITIES_URL}/options`);
    activityOptions = options.activity_types;

    const typeSelect = document.getElementById("activityType");
    const ratingSelect = document.getElementById("easeRating");
    typeSelect.replaceChildren();
    ratingSelect.replaceChildren();

    for (const activity of options.activity_types) {
        typeSelect.add(new Option(activity.label, activity.value));
    }

    ratingSelect.add(new Option("Not rated", ""));
    for (const rating of options.ease_ratings) {
        ratingSelect.add(new Option(`${rating.value} - ${rating.label}`, rating.value));
    }
}


// FORM

function readActivityForm() {
    const name = document.getElementById("activityName").value.trim();
    if (!name) {
        throw new Error("Activity name cannot be empty.");
    }

    const rating = document.getElementById("easeRating").value;
    return {
        name: name,
        activity_type: document.getElementById("activityType").value,
        notes: document.getElementById("activityNotes").value,
        ease_rating: rating === "" ? null : Number(rating)
    };
}

function updateRatingVisibility() {
    const typeSelect = document.getElementById("activityType");
    const ratingSelect = document.getElementById("easeRating");
    const selectedType = activityOptions.find(
        activity => activity.value === typeSelect.value
    );

    const supportsRating = selectedType?.supports_ease_rating === true;
    document.getElementById("ratingField").hidden = !supportsRating;

    if (!supportsRating) {
        ratingSelect.value = "";
    }
}

function setSaveStatus(message, state = "") {
    const status = document.getElementById("saveStatus");
    status.textContent = message;
    status.className = state;
}

function displayActivityForm() {
    const isCurrent = formMode === "current";
    const isEdit = formMode === "edit";
    const isRunning = isCurrent && activeActivity !== null;

    let activity = null;
    if (isCurrent) activity = activeActivity;
    if (isEdit) activity = editingActivity;

    const heading = document.getElementById("activityHeading");
    if (isCurrent) {
        heading.textContent = isRunning ? "Current Activity" : "New Activity";
    } else if (isEdit) {
        heading.textContent = "Edit Activity";
    } else {
        heading.textContent = "Add Past Activity";
    }

    document.getElementById("currentTab").setAttribute("aria-pressed", String(isCurrent));
    document.getElementById("addPastTab").setAttribute("aria-pressed", String(!isCurrent));

    document.getElementById("timer").hidden = !isCurrent;
    document.getElementById("timeFields").hidden = isCurrent;
    document.getElementById("startButton").hidden = !isCurrent || isRunning;
    document.getElementById("saveButton").hidden = isCurrent && !isRunning;
    document.getElementById("stopButton").hidden = !isRunning;
    document.getElementById("deleteButton").hidden = !(isRunning || isEdit);
    document.getElementById("cancelButton").hidden = isCurrent;

    if (activity) {
        document.getElementById("activityName").value = activity.name;
        document.getElementById("activityType").value = activity.activity_type;
        document.getElementById("activityNotes").value = activity.notes ?? "";
        document.getElementById("easeRating").value =
            activity.ease_rating == null ? "" : String(activity.ease_rating);
    } else {
        document.getElementById("activityName").value = "";
        document.getElementById("activityType").selectedIndex = 0;
        document.getElementById("activityNotes").value = "";
        document.getElementById("easeRating").value = "";
    }

    if (isEdit && editingActivity) {
        document.getElementById("startedAt").value =
            toLocalDatetimeInput(editingActivity.started_at);
        document.getElementById("endedAt").value =
            toLocalDatetimeInput(editingActivity.ended_at);
    } else {
        document.getElementById("startedAt").value = "";
        document.getElementById("endedAt").value = "";
    }

    refreshDatetimeDisplays();
    updateRatingVisibility();
    formDirty = false;
    setSaveStatus(isRunning ? "● Saved" : "", isRunning ? "saved" : "");

    if (isCurrent) {
        if (isRunning) {
            updateTimer();
        } else {
            document.getElementById("timer").textContent = "00:00:00";
        }
    }
}

function markUnsaved() {
    if (busy) return;
    if (formMode === "current" && !activeActivity) return;

    formDirty = true;
    setSaveStatus("● Unsaved changes", "unsaved");

    if (formMode !== "current") return;

    clearTimeout(autosaveTimer);
    autosaveTimer = setTimeout(() => {
        autosaveTimer = null;
        runAction(saveCurrentActivity);
    }, AUTOSAVE_DELAY_MS);
}


// HISTORY

async function loadActivities() {
    const activities = await apiRequest(ACTIVITIES_URL);
    const day = getReportingDay();
    const history = await apiRequest(`${ACTIVITIES_URL}?day=${day}`);

    activeActivity = activities.find(activity => activity.ended_at === null) ?? null;

    const completed = history
        .filter(activity => activity.ended_at !== null)
        .sort((a, b) => parseTimestamp(a.started_at) - parseTimestamp(b.started_at));

    const list = document.getElementById("activities");
    list.replaceChildren();

    for (const activity of completed) {
        const item = document.createElement("li");
        const time = document.createElement("span");
        const name = document.createElement("span");
        const details = document.createElement("span");

        time.textContent = `${formatTime(activity.started_at)} – ${formatTime(activity.ended_at)}`;
        name.className = "history-name";
        name.textContent = activity.name;
        name.title = activity.name;
        details.className = "history-details";
        details.textContent = `${activity.activity_type} | ${formatDuration(activity.started_at, activity.ended_at)}`;

        item.append(time, name, details);
        item.tabIndex = 0;
        item.setAttribute("role", "button");
        item.title = "Click to edit";
        item.addEventListener("click", () => changeFormMode("edit", activity));
        item.addEventListener("keydown", event => {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                changeFormMode("edit", activity);
            }
        });
        list.appendChild(item);
    }

    list.scrollTop = list.scrollHeight;
    displayActivityForm();
}


// ACTIONS

async function runAction(action) {
    if (busy) return;

    clearTimeout(autosaveTimer);
    autosaveTimer = null;
    busy = true;

    const controls = document.querySelectorAll("button, input, select, textarea");
    controls.forEach(control => control.disabled = true);

    try {
        await action();
        await loadActivities();
    } catch (error) {
        setSaveStatus(error.message, "error");
    } finally {
        busy = false;
        controls.forEach(control => control.disabled = false);
    }
}

async function saveCurrentActivity() {
    if (!activeActivity) return;

    const data = readActivityForm();
    setSaveStatus("Saving...");

    await apiRequest(`${ACTIVITIES_URL}/${activeActivity.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
    });
    formDirty = false;
}

async function savePastActivity() {
    const data = {
        ...readActivityForm(),
        ...readTimestamps()
    };

    let url = ACTIVITIES_URL;
    let method = "POST";

    if (formMode === "edit") {
        url = `${ACTIVITIES_URL}/${editingActivity.id}`;
        method = "PUT";
    }

    await apiRequest(url, {
        method: method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
    });

    formMode = "current";
    editingActivity = null;
    formDirty = false;
}

async function changeFormMode(mode, activity = null) {
    if (busy) return;
    if (mode === formMode && (mode !== "edit" || activity?.id === editingActivity?.id)) {
        return;
    }

    // Discard edits to a past activity only with confirmation.
    if (formMode !== "current" && formDirty &&
        !window.confirm("Discard unsaved changes?")) {
        return;
    }

    const saveCurrentFirst = formMode === "current" && activeActivity && formDirty;

    await runAction(async () => {
        if (saveCurrentFirst) {
            await saveCurrentActivity();
        }
        formMode = mode;
        editingActivity = mode === "edit" ? activity : null;
        formDirty = false;
    });
}


// EVENT HANDLERS

document.getElementById("activityName").addEventListener("input", markUnsaved);
document.getElementById("activityNotes").addEventListener("input", markUnsaved);
document.getElementById("activityType").addEventListener("change", () => {
    updateRatingVisibility();
    markUnsaved();
});
document.getElementById("easeRating").addEventListener("change", markUnsaved);
for (const [inputId, displayId] of [
    ["startedAt", "startedAtDisplay"],
    ["endedAt", "endedAtDisplay"]
]) {
    const input = document.getElementById(inputId);
    input.addEventListener("input", () => {
        refreshDatetimeDisplay(inputId, displayId);
        markUnsaved();
    });
    input.addEventListener("change", () => {
        refreshDatetimeDisplay(inputId, displayId);
        markUnsaved();
    });
    input.addEventListener("click", () => {
        if (typeof input.showPicker === "function") {
            input.showPicker();
        }
    });
}

document.getElementById("currentTab").addEventListener("click", () => changeFormMode("current"));
document.getElementById("addPastTab").addEventListener("click", () => changeFormMode("add"));
document.getElementById("cancelButton").addEventListener("click", () => changeFormMode("current"));

document.getElementById("startButton").addEventListener("click", () => {
    runAction(async () => {
        const data = readActivityForm();
        await apiRequest(`${ACTIVITIES_URL}/start`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });
    });
});

document.getElementById("saveButton").addEventListener("click", () => {
    runAction(formMode === "current" ? saveCurrentActivity : savePastActivity);
});

document.getElementById("stopButton").addEventListener("click", () => {
    runAction(async () => {
        await saveCurrentActivity();
        await apiRequest(`${ACTIVITIES_URL}/stop`, { method: "POST" });
    });
});

document.getElementById("deleteButton").addEventListener("click", () => {
    const activity = formMode === "edit" ? editingActivity : activeActivity;
    if (!activity || !window.confirm(`Delete "${activity.name}"?`)) return;

    runAction(async () => {
        await apiRequest(`${ACTIVITIES_URL}/${activity.id}`, { method: "DELETE" });
        formMode = "current";
        editingActivity = null;
        formDirty = false;
    });
});


// INITIALIZATION

async function initialize() {
    await loadOptions();
    await loadActivities();
}

initialize().catch(error => setSaveStatus(error.message, "error"));
setInterval(updateTimer, 1000);
