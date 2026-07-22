/**
 * location-picker.js
 * -------------------
 * Reusable click-to-pin location picker, built on Leaflet (same library
 * already used by the analytics map) plus a "use my GPS" button. Lets
 * staff confirm someone's location on their behalf — e.g. a Field Officer
 * registering a walk-in citizen, or a Gov Officer triaging an aid request
 * from someone who never shared a location themselves.
 *
 * Dependency-free beyond Leaflet. Matches the data-attribute-driven
 * convention of entity-picker.js.
 *
 * Two modes:
 *
 *   data-mode="form" — writes into two hidden inputs (named via
 *     data-lat-input / data-lng-input) so a normal form POST picks them
 *     up alongside the rest of the form.
 *
 *   data-mode="api" — POSTs {lat, lng} straight to data-api-url when the
 *     person clicks Confirm, for standalone "confirm this location"
 *     actions that aren't part of a bigger form (e.g. an aid-request
 *     card). On success, replaces the widget with a small confirmation
 *     and optionally reloads the page (data-on-success="reload").
 *
 * Usage:
 *   <div data-location-picker data-mode="form"
 *        data-lat-input="latitude" data-lng-input="longitude"
 *        data-initial-lat="{{ user.latitude or '' }}"
 *        data-initial-lng="{{ user.longitude or '' }}"></div>
 *
 *   <div data-location-picker data-mode="api"
 *        data-api-url="/api/citizens/{{ aid.citizen_user_id }}/location"
 *        data-on-success="reload"></div>
 */
(function () {
  const DEFAULT_CENTER = [7.8731, 80.7718]; // Sri Lanka, roughly — just a sane starting view
  const DEFAULT_ZOOM = 7;
  const PIN_ZOOM = 14;

  function init(container) {
    if (!window.L) {
      container.innerHTML = '<p class="text-xs text-rust">Map library did not load — check your internet connection.</p>';
      return;
    }

    const mode = container.getAttribute('data-mode') || 'form';
    const initialLat = parseFloat(container.getAttribute('data-initial-lat'));
    const initialLng = parseFloat(container.getAttribute('data-initial-lng'));
    const hasInitial = !isNaN(initialLat) && !isNaN(initialLng);

    const wrap = document.createElement('div');
    wrap.className = 'rounded-lg border border-line overflow-hidden';

    const mapEl = document.createElement('div');
    mapEl.style.height = '220px';
    wrap.appendChild(mapEl);

    const bar = document.createElement('div');
    bar.className = 'flex flex-wrap items-center justify-between gap-2 bg-paper px-3 py-2 text-xs';
    const readout = document.createElement('span');
    readout.className = 'font-mono text-slate';
    readout.textContent = hasInitial
      ? `${initialLat.toFixed(5)}, ${initialLng.toFixed(5)}`
      : 'Click the map, or use your current location';
    bar.appendChild(readout);

    const btnRow = document.createElement('div');
    btnRow.className = 'flex gap-2';

    const gpsBtn = document.createElement('button');
    gpsBtn.type = 'button';
    gpsBtn.className = 'btn-ghost !py-1 !px-2 !text-xs';
    gpsBtn.textContent = '📍 Use my location';
    btnRow.appendChild(gpsBtn);

    let confirmBtn = null;
    if (mode === 'api') {
      confirmBtn = document.createElement('button');
      confirmBtn.type = 'button';
      confirmBtn.className = 'btn-primary !py-1 !px-3 !text-xs';
      confirmBtn.textContent = 'Confirm location';
      confirmBtn.disabled = !hasInitial;
      confirmBtn.style.opacity = hasInitial ? '1' : '0.5';
      btnRow.appendChild(confirmBtn);
    }
    bar.appendChild(btnRow);
    wrap.appendChild(bar);
    container.appendChild(wrap);

    // form-mode hidden inputs (created here so callers don't need to hand-write them)
    let latInput = null, lngInput = null;
    if (mode === 'form') {
      const latName = container.getAttribute('data-lat-input') || 'latitude';
      const lngName = container.getAttribute('data-lng-input') || 'longitude';
      latInput = document.createElement('input');
      latInput.type = 'hidden'; latInput.name = latName;
      lngInput = document.createElement('input');
      lngInput.type = 'hidden'; lngInput.name = lngName;
      if (hasInitial) { latInput.value = initialLat; lngInput.value = initialLng; }
      container.appendChild(latInput);
      container.appendChild(lngInput);
    }

    const map = L.map(mapEl).setView(hasInitial ? [initialLat, initialLng] : DEFAULT_CENTER,
                                      hasInitial ? PIN_ZOOM : DEFAULT_ZOOM);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors', maxZoom: 18,
    }).addTo(map);

    let marker = hasInitial ? L.marker([initialLat, initialLng]).addTo(map) : null;

    function setPoint(lat, lng) {
      if (marker) { marker.setLatLng([lat, lng]); }
      else { marker = L.marker([lat, lng]).addTo(map); }
      map.setView([lat, lng], Math.max(map.getZoom(), PIN_ZOOM));
      readout.textContent = `${lat.toFixed(5)}, ${lng.toFixed(5)}`;
      if (mode === 'form') { latInput.value = lat; lngInput.value = lng; }
      if (confirmBtn) { confirmBtn.disabled = false; confirmBtn.style.opacity = '1'; }
    }

    map.on('click', (e) => setPoint(e.latlng.lat, e.latlng.lng));

    gpsBtn.addEventListener('click', () => {
      if (!navigator.geolocation) {
        readout.textContent = 'Your browser does not support GPS location.';
        return;
      }
      gpsBtn.textContent = 'Locating…';
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          gpsBtn.textContent = '📍 Use my location';
          setPoint(pos.coords.latitude, pos.coords.longitude);
        },
        () => {
          gpsBtn.textContent = '📍 Use my location';
          readout.textContent = 'Could not get your location — click the map instead.';
        },
        { enableHighAccuracy: true, timeout: 8000 }
      );
    });

    if (confirmBtn) {
      confirmBtn.addEventListener('click', () => {
        if (!marker) return;
        const { lat, lng } = marker.getLatLng();
        const apiUrl = container.getAttribute('data-api-url');
        confirmBtn.disabled = true;
        confirmBtn.textContent = 'Saving…';
        fetch(apiUrl, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ lat, lng }),
        })
          .then((r) => r.json().then((data) => ({ ok: r.ok, data })))
          .then(({ ok, data }) => {
            if (!ok) throw new Error(data.error || 'Failed to save location');
            confirmBtn.textContent = '✅ Saved';
            const onSuccess = container.getAttribute('data-on-success');
            if (onSuccess === 'reload') setTimeout(() => window.location.reload(), 600);
          })
          .catch((err) => {
            confirmBtn.disabled = false;
            confirmBtn.textContent = 'Confirm location';
            readout.textContent = err.message;
          });
      });
    }

    // Leaflet needs a resize nudge when its container was hidden/animated in
    setTimeout(() => map.invalidateSize(), 150);
  }

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-location-picker]').forEach(init);
    document.querySelectorAll('[data-request-location-btn]').forEach(initRequestButton);
  });

  /**
   * "Ask citizen to share their location" button — sends a Telegram
   * message with the native location-share prompt (see
   * telegram_api.send_location_request). Separate from the map picker
   * above: this asks the citizen's own device for their own position,
   * rather than letting staff drop a pin on someone else's behalf.
   */
  function initRequestButton(btn) {
    const statusEl = btn.parentElement.querySelector('[data-request-location-status]');
    btn.addEventListener('click', () => {
      const apiUrl = btn.getAttribute('data-api-url');
      const aidRequestId = btn.getAttribute('data-aid-request-id') || null;
      btn.disabled = true;
      const original = btn.textContent;
      btn.textContent = 'Asking…';
      fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ aid_request_id: aidRequestId }),
      })
        .then((r) => r.json().then((data) => ({ ok: r.ok, data })))
        .then(({ ok, data }) => {
          if (!ok) throw new Error(data.error || 'Could not send the request');
          btn.textContent = '✅ Asked — waiting for their reply';
          if (statusEl) { statusEl.textContent = 'They\u2019ll get a Telegram message asking them to share their location.'; }
        })
        .catch((err) => {
          btn.disabled = false;
          btn.textContent = original;
          if (statusEl) { statusEl.textContent = err.message; statusEl.classList.add('text-rust'); }
        });
    });
  }
})();
