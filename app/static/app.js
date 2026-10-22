
const ACTIVITIES_URL = "/activities";
const AUTOSAVE_DELAY_MS = 5000;
const REPORTING_DAY_START_HOUR = 5;

let activeActivity = null;
let busy = false;
let autosaveTimer = null;


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
    const duration = parseTimestamp(endedAt) - parseTimestamp(startedAt);

    const minutes = Math.max(0, Math.floor(duration / 60000));
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;

    if (hours > 0) {
        return `${hours}h ${remainingMinutes}m`;
    }

    return `${minutes}m`;
}

function updateTimer() {
    if (!activeActivity) return;

    const started = parseTimestamp(activeActivity.started_at);

    const elapsed = Math.max(
        0,
        Math.floor((Date.now() - started.getTime()) / 1000)
    );

    const hours = Math.floor(elapsed / 3600);
    const minutes = Math.floor((elapsed % 3600) / 60);
    const seconds = elapsed % 60;

    const pad = value => String(value).padStart(2, "0");

    document.getElementById("timer").textContent =
        `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
}


// SAVE STATUS

function setSaveStatus(message, state = "") {
    const status = document.getElementById("saveStatus");

    status.textContent = message;
    status.className = state;
}

function markUnsaved() {
    if (!activeActivity || busy) return;

    setSaveStatus("● Unsaved changes", "unsaved");

    clearTimeout(autosaveTimer);

    autosaveTimer = setTimeout(() => {
        autosaveTimer = null;
        runAction(saveCurrentActivity);
    }, AUTOSAVE_DELAY_MS);
}

document.getElementById("activityName")
    .addEventListener("input", markUnsaved);

document.getElementById("activityNotes")
    .addEventListener("input", markUnsaved);

document.getElementById("activityType")
    .addEventListener("change", () => {
        updateRatingVisibility();
        markUnsaved();
    });

document.getElementById("easeRating")
    .addEventListener("change", markUnsaved);


// API

async function apiRequest(url, options = {}) {
    const response = await fetch(url, options);

    if (!response.ok) {
        throw new Error(`Request failed: HTTP ${response.status}`);
    }

    return response.json();
}

let activityOptions = [];

async function loadOptions() {
    const options = await apiRequest("/options");

    activityOptions = options.activity_types;

    const typeSelect = document.getElementById("activityType");
    const ratingSelect = document.getElementById("easeRating");

    typeSelect.replaceChildren();
    ratingSelect.replaceChildren();

    // Activity types
    for (const activity of options.activity_types) {
        typeSelect.add(new Option(activity.label, activity.value));
    }

    // Optional rating
    ratingSelect.add(new Option("Not rated", ""));

    for (const rating of options.ease_ratings) {
        ratingSelect.add(
            new Option(`${rating.value} - ${rating.label}`, rating.value)
        );
    }

    updateRatingVisibility();
}

// FORM

function readActivityForm() {
    const name =
        document.getElementById("activityName").value.trim();

    const activityType =
        document.getElementById("activityType").value;

    const notes =
        document.getElementById("activityNotes").value;

    const rating = document.getElementById("easeRating").value;

    if (!name) {
        throw new Error("Activity name cannot be empty.");
    }

    return {
        name: name,
        activity_type: activityType,
        notes: notes,
        ease_rating: rating === "" ? null : Number(rating)
    };
}

function displayActivityForm() {
    const isRunning = activeActivity !== null;

    document.getElementById("activityHeading").textContent =
        isRunning ? "Current Activity" : "New Activity";

    document.getElementById("startButton").hidden = isRunning;
    document.getElementById("saveButton").hidden = !isRunning;
    document.getElementById("stopButton").hidden = !isRunning;

    if (isRunning) {
        document.getElementById("activityName").value =
            activeActivity.name;

        document.getElementById("activityType").value =
            activeActivity.activity_type;

        document.getElementById("activityNotes").value =
            activeActivity.notes ?? "";

        document.getElementById("easeRating").value =
            activeActivity.ease_rating == null
                ? ""
                : String(activeActivity.ease_rating);

        updateRatingVisibility();
        setSaveStatus("● Saved", "saved");
        updateTimer();
    } else {
        document.getElementById("activityName").value = "";
        document.getElementById("activityType").selectedIndex = 0;
        document.getElementById("activityNotes").value = "";
        document.getElementById("timer").textContent = "00:00:00";
        document.getElementById("easeRating").value = "";
        updateRatingVisibility();

        setSaveStatus("");
    }
}

function getReportingDay() {
    const date = new Date();

    // Before 05:00, we're still in the previous reporting day.
    if (date.getHours() < REPORTING_DAY_START_HOUR) {
        date.setDate(date.getDate() - 1);
    }

    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");

    return `${year}-${month}-${day}`;
}


// LOAD ACTIVITIES

async function loadActivities() {
    const activities = await apiRequest(ACTIVITIES_URL);

    const reportingDay = getReportingDay();
    const historyActivities = await apiRequest(`${ACTIVITIES_URL}?day=${reportingDay}`);

    activeActivity = activities.find(
        activity => activity.ended_at === null
    ) ?? null;

    displayActivityForm();

    const completed = historyActivities
        .filter(activity => activity.ended_at !== null)
        .sort((a, b) =>
            parseTimestamp(a.started_at) -
            parseTimestamp(b.started_at)
        );

    const list = document.getElementById("activities");
    list.replaceChildren();

    for (const activity of completed) {
        const item = document.createElement("li");

        const time = document.createElement("span");
        time.textContent =
            `${formatTime(activity.started_at)} – ${formatTime(activity.ended_at)}`;

        const name = document.createElement("span");
        name.className = "history-name";
        name.textContent = activity.name;
        name.title = activity.name;

        const details = document.createElement("span");
        details.className = "history-details";
        const type = document.createElement("span");
        type.textContent = activity.activity_type;

        const separator = document.createElement("span");
        separator.textContent = "|";

        const duration = document.createElement("span");
        duration.textContent = formatDuration(activity.started_at, activity.ended_at);

        details.append(type, separator, duration);

        item.append(time, name, details);
        list.appendChild(item);
    }

    // Show the most recent history entries.
    list.scrollTop = list.scrollHeight;
}

function updateRatingVisibility() {
    const typeSelect = document.getElementById("activityType");
    const ratingSelect = document.getElementById("easeRating");
    const ratingField = document.getElementById("ratingField");

    const selectedType = activityOptions.find(
        activity => activity.value === typeSelect.value
    );

    const supportsRating = selectedType?.supports_ease_rating === true;

    ratingField.hidden = !supportsRating;

    if (!supportsRating) {
        ratingSelect.value = "";
    }
}


// SAVE CURRENT ACTIVITY

async function saveCurrentActivity() {
    if (!activeActivity) return;

    const data = readActivityForm();

    setSaveStatus("Saving...");

    try {
        await apiRequest(`${ACTIVITIES_URL}/${activeActivity.id}`, {
            method: "PUT",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(data)
        });

        setSaveStatus("● Saved", "saved");
    } catch (error) {
        setSaveStatus("● Save failed", "error");
        throw error;
    }
}


// BUTTON HANDLING

async function runAction(action) {
    clearTimeout(autosaveTimer);
    autosaveTimer = null;

    if (busy) return;

    busy = true;

    const controls = document.querySelectorAll(
        "button, input, select, textarea"
    );

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


// START

document.getElementById("startButton").addEventListener("click", () => {
    runAction(async () => {
        const data = readActivityForm();
   
        await apiRequest(`${ACTIVITIES_URL}/start`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(data)
        });
    });
});


// SAVE

document.getElementById("saveButton").addEventListener("click", () => {
    runAction(async () => {
        await saveCurrentActivity();
    });
});


// STOP

document.getElementById("stopButton").addEventListener("click", () => {
    runAction(async () => {
        await saveCurrentActivity();

        await apiRequest(`${ACTIVITIES_URL}/stop`, {
            method: "POST"
        });
    });
});


// INITIALIZATION

async function initialize() {
    await loadOptions();
    await loadActivities();
}

initialize().catch(error => {
    setSaveStatus(error.message, "error");
});

setInterval(updateTimer, 1000);
