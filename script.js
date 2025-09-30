const endpoints = {
    states: "/api/states",
    districts: (state) => `/api/districts/${state}`,
    talukas: (state, district) => `/api/talukas/${state}/${district}`,
    villages: (state, district, taluka) =>
        `/api/villages/${state}/${district}/${taluka}`,
    distance: (srcFull, dstFull) =>
        `/api/distance?src=${srcFull}&dest=${dstFull}`,
    location: (state, district, taluka, village) =>
        `/api/location/${state}/${district}/${taluka}/${village}`,
};

function $(id) {
    return document.getElementById(id);
}

async function fetchJson(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error("Network error: " + res.status);
    return await res.json();
}

// Populate states for both src and dst
async function loadStates() {
    console.log("Loading............");
    const states = await fetchJson(endpoints.states);
    console.log("🚀 ~ loadStates ~ states:", states);

    ["src_state", "dst_state"].forEach((id) => {
        const sel = $(id);
        sel.innerHTML = '<option value="">-- select state --</option>';
        states.forEach((s) => {
            const opt = document.createElement("option");
            opt.value = s.code;
            opt.text = `${s.code} ${s.name}`;
            sel.appendChild(opt);
        });
    });
}

async function loadDistricts(side, stateCode) {
    const selId = side === "src" ? "src_district" : "dst_district";
    const talId = side === "src" ? "src_taluka" : "dst_taluka";
    const vilId = side === "src" ? "src_village" : "dst_village";
    const sel = $(selId);
    sel.innerHTML = '<option value="">-- select district --</option>';
    $(talId).innerHTML = '<option value="">-- none --</option>';
    $(vilId).innerHTML = '<option value="">-- none --</option>';
    if (!stateCode) return;
    const districts = await fetchJson(endpoints.districts(stateCode));
    districts.forEach((d) => {
        const opt = document.createElement("option");
        opt.value = d.code;
        opt.text = `${d.code} ${d.name}`;
        sel.appendChild(opt);
    });
}

async function loadTalukas(side, stateCode, districtCode) {
    const talId = side === "src" ? "src_taluka" : "dst_taluka";
    const vilId = side === "src" ? "src_village" : "dst_village";
    const sel = $(talId);
    sel.innerHTML = '<option value="">-- none --</option>';
    $(vilId).innerHTML = '<option value="">-- none --</option>';
    if (!stateCode || !districtCode) return;
    const talukas = await fetchJson(endpoints.talukas(stateCode, districtCode));
    talukas.forEach((t) => {
        const opt = document.createElement("option");
        opt.value = t.code;
        opt.text = `${t.code} ${t.name}`;
        sel.appendChild(opt);
    });
}

async function loadVillages(side, stateCode, districtCode, talukaCode) {
    const vilId = side === "src" ? "src_village" : "dst_village";
    const sel = $(vilId);
    sel.innerHTML = '<option value="">-- none --</option>';
    if (!stateCode || !districtCode || !talukaCode) return;
    const villages = await fetchJson(
        endpoints.villages(stateCode, districtCode, talukaCode)
    );
    villages.forEach((v) => {
        const opt = document.createElement("option");
        opt.value = v.code;
        opt.dataset.full = v.full_code || "";
        opt.text = `${v.code} ${v.name}`;
        sel.appendChild(opt);
    });
}

// Helper to build full_code (state(2) + district(2) + taluka(2 or '00') + village(3 or '000'))
function buildFullCode(state, district, taluka, village) {
    if (!state || !district) return null;
    const s = state && state !== "" ? state.padStart(2, "0") : "00";
    const d = district && district !== "" ? district.padStart(2, "0") : "00";
    const t = taluka && taluka !== "" ? taluka.padStart(2, "0") : "00";
    const v = village && village !== "" ? village.padStart(3, "0") : "000";
    return `${s}${d}${t}${v}`;
}

async function getDistanceAndShow() {
    const s_state = $("src_state").value;
    const s_district = $("src_district").value;
    const s_taluka = $("src_taluka").value;
    const s_village = $("src_village").value;

    const d_state = $("dst_state").value;
    const d_district = $("dst_district").value;
    const d_taluka = $("dst_taluka").value;
    const d_village = $("dst_village").value;

    const srcFull = buildFullCode(s_state, s_district, s_taluka, s_village);
   
    const dstFull = buildFullCode(d_state, d_district, d_taluka, d_village);

    if (!srcFull || !dstFull) {
        alert(
            "Please select at least state and district for both source and destination"
        );
        return;
    }

    // Call backend distance endpoint
    try {
        const res = await fetchJson(endpoints.distance(srcFull, dstFull));
        console.log("🚀 ~ getDistanceAndShow ~ res:", res);
        $("db_distance").innerText = res.database_distance_km ?? "-";
        $("gmaps_distance").innerText = res.google_maps_distance_km ?? "-";
    } catch (e) {
        alert("Failed to fetch distance: " + e.message);
    }
}

async function openRouteOnMaps() {
    // Build full codes and then fetch lat/lng from backend
    const s_state = $("src_state").value;
    const s_district = $("src_district").value;
    const s_taluka = $("src_taluka").value;
    const s_village = $("src_village").value;

    const d_state = $("dst_state").value;
    const d_district = $("dst_district").value;
    const d_taluka = $("dst_taluka").value;
    const d_village = $("dst_village").value;

    const srcFull = buildFullCode(s_state, s_district, s_taluka, s_village);
    const dstFull = buildFullCode(d_state, d_district, d_taluka, d_village);
    if (!srcFull || !dstFull) {
        alert("Select state+district for both sides");
        return;
    }

    try {
        const sLoc = await fetchJson(endpoints.location(srcFull));
        const dLoc = await fetchJson(endpoints.location(dstFull));
        if (!sLoc || !dLoc || !sLoc.latitude || !dLoc.latitude) {
            alert("Latitude/Longitude not found for one or both locations");
            return;
        }
        const origin = `${sLoc.latitude},${sLoc.longitude}`;
        const dest = `${dLoc.latitude},${dLoc.longitude}`;
        const url = `https://www.google.com/maps/dir/?api=1&origin=${encodeURIComponent(
            origin
        )}&destination=${encodeURIComponent(dest)}&travelmode=driving`;
        window.open(url, "_blank");
    } catch (e) {
        alert("Failed to open maps: " + e.message);
    }
}

window.addEventListener("load", async () => {
    await loadStates();

    // Wire up events for source side
    $("src_state").addEventListener("change", async (e) => {
        await loadDistricts("src", e.target.value);
    });
    $("src_district").addEventListener("change", async (e) => {
        const s = $("src_state").value;
        await loadTalukas("src", s, e.target.value);
    });
    $("src_taluka").addEventListener("change", async (e) => {
        const s = $("src_state").value;
        const d = $("src_district").value;
        await loadVillages("src", s, d, e.target.value);
    });

    // Destination side
    $("dst_state").addEventListener("change", async (e) => {
        await loadDistricts("dst", e.target.value);
    });
    $("dst_district").addEventListener("change", async (e) => {
        const s = $("dst_state").value;
        await loadTalukas("dst", s, e.target.value);
    });
    $("dst_taluka").addEventListener("change", async (e) => {
        const s = $("dst_state").value;
        const d = $("dst_district").value;
        await loadVillages("dst", s, d, e.target.value);
    });

    $("btn_get_distance").addEventListener("click", getDistanceAndShow);
    $("btn_show_map").addEventListener("click", openRouteOnMaps);
});
