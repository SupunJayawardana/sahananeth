/**
 * entity-picker.js
 * -----------------
 * Minimal typeahead used anywhere a form needs to search existing
 * beneficiaries/users instead of only exact-matching on submit.
 *
 * Usage:
 *   <input type="text" data-entity-picker="beneficiaries"
 *          data-fill="identification_number:identification_number,full_name:label">
 *
 * data-entity-picker: which /api/lookup/<...> endpoint to query
 * data-fill: comma-separated "formFieldName:resultKey" pairs — for each
 *            pair, the named sibling form field gets set to
 *            result[resultKey] when a suggestion is picked. resultKey is
 *            one of: id, label, sublabel, identification_number.
 *
 * Kept dependency-free on purpose — the rest of the stack is
 * server-rendered Jinja + Tailwind, so a heavier library isn't warranted.
 */
(function () {
  function debounce(fn, wait) {
    let t;
    return function (...args) {
      clearTimeout(t);
      t = setTimeout(() => fn.apply(this, args), wait);
    };
  }

  function initPicker(input) {
    const endpoint = input.getAttribute('data-entity-picker');
    const fillSpec = input.getAttribute('data-fill') || '';
    const form = input.closest('form');
    const fillPairs = fillSpec.split(',').map((s) => s.trim()).filter(Boolean).map((pair) => {
      const [fieldName, resultKey] = pair.split(':');
      return { fieldName, resultKey, el: form ? form.querySelector(`[name="${fieldName}"]`) : null };
    });

    const box = document.createElement('div');
    box.className = 'entity-picker-results';
    box.style.cssText = 'position:relative;';
    input.parentNode.insertBefore(box, input.nextSibling);

    const list = document.createElement('div');
    list.style.cssText = 'position:absolute;z-index:40;left:0;right:0;top:2px;background:#fff;' +
      'border:1px solid #e5e0d8;border-radius:8px;box-shadow:0 4px 14px rgba(0,0,0,.08);' +
      'max-height:220px;overflow-y:auto;display:none;';
    box.appendChild(list);

    function hide() { list.style.display = 'none'; list.innerHTML = ''; }

    async function search(q) {
      if (!q || q.length < 2) { hide(); return; }
      let res;
      try {
        res = await fetch(`/api/lookup/${endpoint}?q=${encodeURIComponent(q)}`);
      } catch (e) { hide(); return; }
      if (!res.ok) { hide(); return; }
      const data = await res.json();
      if (!data.results || !data.results.length) { hide(); return; }

      list.innerHTML = '';
      data.results.forEach((r) => {
        const row = document.createElement('div');
        row.style.cssText = 'padding:8px 12px;cursor:pointer;font-size:13px;';
        row.onmouseenter = () => row.style.background = '#f4efe6';
        row.onmouseleave = () => row.style.background = '';
        row.innerHTML = `<div style="font-weight:600;color:#2a2a28;">${r.label}</div>` +
          (r.sublabel ? `<div style="color:#8a8378;font-size:12px;">${r.sublabel}</div>` : '');
        row.onclick = () => {
          input.value = r.label;
          fillPairs.forEach(({ el, resultKey }) => {
            if (el && resultKey in r) el.value = r[resultKey];
          });
          input.dataset.selectedId = r.id;
          hide();
        };
        list.appendChild(row);
      });
      list.style.display = 'block';
    }

    input.addEventListener('input', debounce((e) => search(e.target.value), 250));
    document.addEventListener('click', (e) => {
      if (!box.contains(e.target) && e.target !== input) hide();
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-entity-picker]').forEach(initPicker);
  });
})();
