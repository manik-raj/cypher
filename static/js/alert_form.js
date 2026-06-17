(function () {
  const cfg = window.CYPHER || { exchanges: [], operators: [], existingConditions: [] };

  const exchangeOptions = (selected) =>
    cfg.exchanges
      .map(([code, label]) => `<option value="${code}" ${code === selected ? "selected" : ""}>${label}</option>`)
      .join("");

  const operatorOptions = (selected) =>
    cfg.operators
      .map((op) => `<option value="${op}" ${op === selected ? "selected" : ""}>${op}</option>`)
      .join("");

  const container = document.getElementById("conditions");

  function rowTemplate(c) {
    c = c || {};
    const metric = c.left_metric || "funding_fee";
    const rtype = c.right_type || "constant";
    const wrap = document.createElement("div");
    wrap.className = "border rounded p-2 mb-2 condition-row";
    wrap.innerHTML = `
      <div class="row g-2 align-items-end">
        <div class="col-md-3">
          <label class="form-label small mb-0">Left side</label>
          <select class="form-select form-select-sm cond-metric" name="cond_left_metric">
            <option value="funding_fee" ${metric === "funding_fee" ? "selected" : ""}>Funding fee of…</option>
            <option value="difference" ${metric === "difference" ? "selected" : ""}>Difference (primary − secondary)</option>
          </select>
        </div>
        <div class="col-md-2 cond-left-exchange">
          <label class="form-label small mb-0">Exchange</label>
          <select class="form-select form-select-sm" name="cond_left_exchange">${exchangeOptions(c.left_exchange)}</select>
        </div>
        <div class="col-md-2">
          <label class="form-label small mb-0">Operator</label>
          <select class="form-select form-select-sm" name="cond_operator">${operatorOptions(c.operator)}</select>
        </div>
        <div class="col-md-2">
          <label class="form-label small mb-0">Compare to</label>
          <select class="form-select form-select-sm cond-rtype" name="cond_right_type">
            <option value="constant" ${rtype === "constant" ? "selected" : ""}>a value</option>
            <option value="exchange" ${rtype === "exchange" ? "selected" : ""}>an exchange</option>
          </select>
        </div>
        <div class="col-md-2 cond-right-value">
          <label class="form-label small mb-0">Value (%)</label>
          <input class="form-control form-control-sm" type="number" step="any" name="cond_right_value" value="${c.right_value != null ? c.right_value : ""}">
        </div>
        <div class="col-md-2 cond-right-exchange">
          <label class="form-label small mb-0">Exchange</label>
          <select class="form-select form-select-sm" name="cond_right_exchange">${exchangeOptions(c.right_exchange)}</select>
        </div>
        <div class="col-md-1">
          <button type="button" class="btn btn-sm btn-outline-danger remove-condition">&times;</button>
        </div>
      </div>`;

    const metricSel = wrap.querySelector(".cond-metric");
    const rtypeSel = wrap.querySelector(".cond-rtype");
    const syncRow = () => {
      wrap.querySelector(".cond-left-exchange").style.display =
        metricSel.value === "funding_fee" ? "" : "none";
      wrap.querySelector(".cond-right-value").style.display =
        rtypeSel.value === "constant" ? "" : "none";
      wrap.querySelector(".cond-right-exchange").style.display =
        rtypeSel.value === "exchange" ? "" : "none";
    };
    metricSel.addEventListener("change", syncRow);
    rtypeSel.addEventListener("change", syncRow);
    wrap.querySelector(".remove-condition").addEventListener("click", () => wrap.remove());
    syncRow();
    return wrap;
  }

  function addCondition(data) {
    container.appendChild(rowTemplate(data));
  }

  document.getElementById("add-condition").addEventListener("click", () => addCondition());

  // Render existing conditions (edit / re-render after validation error).
  (cfg.existingConditions || []).forEach(addCondition);

  // Toggle conditional vs scheduled sections.
  const condSection = document.getElementById("conditional-section");
  const schedSection = document.getElementById("scheduled-section");
  function syncType() {
    const isScheduled = document.getElementById("type-sched").checked;
    condSection.style.display = isScheduled ? "none" : "";
    schedSection.style.display = isScheduled ? "" : "none";
    if (!isScheduled && container.children.length === 0) addCondition();
  }
  document.getElementById("type-cond").addEventListener("change", syncType);
  document.getElementById("type-sched").addEventListener("change", syncType);

  // Toggle daily vs interval fields.
  function syncSchedule() {
    const isInterval = document.getElementById("sk-interval").checked;
    document.getElementById("daily-field").style.display = isInterval ? "none" : "";
    document.getElementById("interval-field").style.display = isInterval ? "" : "none";
  }
  document.getElementById("sk-daily").addEventListener("change", syncSchedule);
  document.getElementById("sk-interval").addEventListener("change", syncSchedule);

  syncType();
  syncSchedule();
})();
