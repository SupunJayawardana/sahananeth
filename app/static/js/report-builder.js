/**
 * report-builder.js
 * ------------------
 * Drives the filter rows on the Report Builder form. Each row has a
 * field <select>, an operator <select>, and a value input whose shape
 * depends on the chosen field's type (text, a Yes/No select for
 * booleans, a choice <select> for enum fields, a date/number input,
 * or nothing at all for "is empty"/"is not empty").
 *
 * Field metadata (type, and choice-field options) is embedded on the
 * page as a small JSON blob (see report_builder.html) rather than
 * fetched — the field list is already known server-side once a source
 * is chosen, so there's no need for another round trip.
 */
(function () {
  function operatorsFor(type) {
    const OPS = {
      string:  [['contains', 'contains'], ['not_contains', "doesn't contain"], ['equals', 'is exactly'],
                ['is_empty', 'is empty'], ['is_not_empty', 'is not empty']],
      choice:  [['equals', 'is'], ['not_equals', 'is not']],
      number:  [['equals', '='], ['greater_than', '>'], ['less_than', '<']],
      boolean: [['is_true', 'Yes'], ['is_false', 'No']],
      date:    [['within_last_days', 'within the last N days'], ['older_than_days', 'older than N days'],
                ['before', 'before date'], ['after', 'after date']],
    };
    return OPS[type] || [];
  }

  function valueInputFor(row, type, choices, currentValue) {
    const holder = row.querySelector('[data-value-holder]');
    holder.innerHTML = '';
    if (type === 'choice' && choices) {
      const sel = document.createElement('select');
      sel.name = 'value'; sel.className = 'w-full rounded-lg border border-line bg-paper px-3 py-2 text-sm';
      choices.forEach((c) => {
        const opt = document.createElement('option');
        opt.value = c; opt.textContent = c.replace(/_/g, ' ');
        if (c === currentValue) opt.selected = true;
        sel.appendChild(opt);
      });
      holder.appendChild(sel);
    } else if (type === 'boolean') {
      // the operator itself (is_true/is_false) carries the meaning — no separate value needed
      const hint = document.createElement('p');
      hint.className = 'text-xs text-slate italic pt-2';
      hint.textContent = 'No value needed — the option above already says Yes or No.';
      holder.appendChild(hint);
    } else {
      const inp = document.createElement('input');
      inp.name = 'value';
      inp.className = 'w-full rounded-lg border border-line bg-paper px-3 py-2 text-sm';
      if (type === 'number') { inp.type = 'number'; inp.step = 'any'; }
      else if (type === 'date') { inp.type = 'text'; inp.placeholder = 'YYYY-MM-DD or number of days'; }
      else { inp.type = 'text'; }
      if (currentValue !== undefined && currentValue !== null) inp.value = currentValue;
      holder.appendChild(inp);
    }
  }

  function refreshRow(row, fieldMeta, presetOperator, presetValue) {
    const fieldSel = row.querySelector('[data-filter-field]');
    const opSel = row.querySelector('[data-filter-operator]');
    const fieldKey = fieldSel.value;
    const meta = fieldMeta[fieldKey];
    if (!meta) { opSel.innerHTML = ''; row.querySelector('[data-value-holder]').innerHTML = ''; return; }

    opSel.innerHTML = '';
    operatorsFor(meta.type).forEach(([val, label]) => {
      const opt = document.createElement('option');
      opt.value = val; opt.textContent = label;
      if (val === presetOperator) opt.selected = true;
      opSel.appendChild(opt);
    });

    const chosenOp = presetOperator || opSel.value;
    const needsValue = !['is_empty', 'is_not_empty', 'is_true', 'is_false'].includes(chosenOp) || meta.type === 'boolean';
    valueInputFor(row, meta.type, meta.choices, presetValue);
    if (!needsValue) row.querySelector('[data-value-holder]').style.display = 'none';
    else row.querySelector('[data-value-holder]').style.display = '';
  }

  document.addEventListener('DOMContentLoaded', () => {
    const metaEl = document.getElementById('report-field-meta');
    if (!metaEl) return;
    const fieldMeta = JSON.parse(metaEl.textContent);

    document.querySelectorAll('[data-filter-row]').forEach((row) => {
      const preset = row.getAttribute('data-preset');
      const presetData = preset ? JSON.parse(preset) : {};
      refreshRow(row, fieldMeta, presetData.operator, presetData.value);

      row.querySelector('[data-filter-field]').addEventListener('change', () => refreshRow(row, fieldMeta));
      row.querySelector('[data-filter-operator]').addEventListener('change', () => refreshRow(row, fieldMeta,
        row.querySelector('[data-filter-operator]').value));
    });

    let visibleRows = document.querySelectorAll('[data-filter-row]:not(.hidden)').length;
    const addBtn = document.getElementById('add-filter-row');
    const allRows = document.querySelectorAll('[data-filter-row]');
    if (addBtn) {
      addBtn.addEventListener('click', () => {
        if (visibleRows < allRows.length) {
          allRows[visibleRows].classList.remove('hidden');
          visibleRows += 1;
          if (visibleRows >= allRows.length) addBtn.style.display = 'none';
        }
      });
    }

    document.querySelectorAll('[data-remove-filter-row]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const row = btn.closest('[data-filter-row]');
        row.querySelector('[data-filter-field]').selectedIndex = 0;
        row.classList.add('hidden');
        if (addBtn) addBtn.style.display = '';
      });
    });

    // Location filter section toggle
    const locToggle = document.getElementById('loc-filter-toggle');
    const locSection = document.getElementById('loc-filter-section');
    if (locToggle && locSection) {
      const sync = () => { locSection.style.display = locToggle.checked ? '' : 'none'; };
      locToggle.addEventListener('change', sync);
      sync();
    }

    // Group-by hides sort controls (they're meaningless together)
    const groupBySel = document.getElementById('group_by');
    const sortSection = document.getElementById('sort-section');
    if (groupBySel && sortSection) {
      const sync = () => { sortSection.style.display = groupBySel.value ? 'none' : ''; };
      groupBySel.addEventListener('change', sync);
      sync();
    }
  });
})();
