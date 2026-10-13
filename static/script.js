/**
 * Gift Decision Agent — Client JavaScript
 * Manages form state, LangGraph API orchestration, feedback loops, and PDF downloads.
 */

document.addEventListener("DOMContentLoaded", () => {
  let currentSessionId = null;

  // DOM Elements
  const modeBadge = document.getElementById("mode-badge");
  const modeLabel = document.getElementById("mode-label");
  const form = document.getElementById("gift-discovery-form");
  const btnSubmit = document.getElementById("btn-submit");
  const btnSpinner = btnSubmit.querySelector(".btn-spinner");

  const stateEmpty = document.getElementById("state-empty");
  const stateLoading = document.getElementById("state-loading");
  const stateResults = document.getElementById("state-results");
  const loadingStageTitle = document.getElementById("loading-stage-title");

  const interestTagContainer = document.getElementById("interest-tag-container");
  const customInterestInput = document.getElementById("custom-interest-input");
  const btnAddInterest = document.getElementById("btn-add-interest");
  const preferenceContainer = document.getElementById("preference-container");

  const budgetMinInput = document.getElementById("budget-min");
  const budgetMaxInput = document.getElementById("budget-max");
  const presetPills = document.querySelectorAll(".preset-pill");

  const btnToggleAdvanced = document.getElementById("btn-toggle-advanced");
  const advancedFields = document.getElementById("advanced-fields");

  const btnDownloadPdf = document.getElementById("btn-download-pdf");
  const btnViewWorkflow = document.getElementById("btn-view-workflow");
  const workflowModal = document.getElementById("workflow-modal");
  const btnCloseModal = document.getElementById("btn-close-modal");
  const workflowTabs = document.querySelectorAll(".w-tab");

  // 1. Initial Health Check
  async function checkHealth() {
    try {
      const res = await fetch("/health");
      if (res.ok) {
        const data = await res.json();
        modeBadge.className = "mode-badge";
        if (data.mode === "gemini") {
          modeBadge.classList.add("gemini-active");
          modeLabel.textContent = `Gemini AI (${data.model})`;
        } else {
          modeBadge.classList.add("fallback-active");
          modeLabel.textContent = "Deterministic Fallback Mode";
        }
      }
    } catch (e) {
      console.warn("Health check error:", e);
      modeBadge.className = "mode-badge fallback-active";
      modeLabel.textContent = "Deterministic Engine Active";
    }
  }
  checkHealth();

  // 2. Budget Presets
  presetPills.forEach(pill => {
    pill.addEventListener("click", () => {
      presetPills.forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      budgetMinInput.value = pill.dataset.min;
      budgetMaxInput.value = pill.dataset.max;
    });
  });

  // 3. Interest Tag Toggling
  interestTagContainer.addEventListener("click", (e) => {
    const chip = e.target.closest(".tag-chip");
    if (chip) {
      chip.classList.toggle("active");
    }
  });

  // Add Custom Interest Tag
  function addCustomInterest() {
    const val = customInterestInput.value.trim();
    if (!val) return;
    
    // Check if already exists
    const existing = Array.from(interestTagContainer.querySelectorAll(".tag-chip"))
      .some(chip => chip.dataset.val.toLowerCase() === val.toLowerCase());
    
    if (!existing) {
      const newChip = document.createElement("button");
      newChip.type = "button";
      newChip.className = "tag-chip active";
      newChip.dataset.val = val;
      newChip.textContent = val;
      interestTagContainer.appendChild(newChip);
    }
    customInterestInput.value = "";
  }

  btnAddInterest.addEventListener("click", addCustomInterest);
  customInterestInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      addCustomInterest();
    }
  });

  // 4. Preference Vibe Toggling
  preferenceContainer.addEventListener("click", (e) => {
    const chip = e.target.closest(".tag-chip");
    if (chip) {
      chip.classList.toggle("active");
    }
  });

  // 5. Accordion Toggle
  btnToggleAdvanced.addEventListener("click", () => {
    btnToggleAdvanced.classList.toggle("open");
    advancedFields.classList.toggle("hidden");
  });

  // 6. Form Submission
  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    // Reset error messages
    document.querySelectorAll(".field-error").forEach(el => el.textContent = "");

    const occasion = document.getElementById("occasion-select").value;
    const recipient = document.getElementById("recipient-select").value;
    const relationship = document.getElementById("relationship-select").value;
    const giftType = document.getElementById("gift-type-select").value;

    const budgetMin = parseFloat(budgetMinInput.value) || 0;
    const budgetMax = parseFloat(budgetMaxInput.value) || 0;

    let hasErrors = false;
    if (!occasion) {
      document.getElementById("err-occasion").textContent = "Please select an occasion.";
      hasErrors = true;
    }
    if (!recipient) {
      document.getElementById("err-recipient").textContent = "Please select a recipient.";
      hasErrors = true;
    }
    if (budgetMax <= 0 || budgetMax < budgetMin) {
      document.getElementById("err-budget").textContent = "Max budget must be greater than or equal to Min budget.";
      hasErrors = true;
    }

    const selectedInterests = Array.from(interestTagContainer.querySelectorAll(".tag-chip.active"))
      .map(c => c.dataset.val);

    if (selectedInterests.length === 0) {
      document.getElementById("err-interests").textContent = "Please select at least one interest.";
      hasErrors = true;
    }

    if (hasErrors) return;

    const selectedPreferences = Array.from(preferenceContainer.querySelectorAll(".tag-chip.active"))
      .map(c => c.dataset.val);

    const dislikedRaw = document.getElementById("disliked-input").value;
    const dislikedItems = dislikedRaw ? dislikedRaw.split(",").map(s => s.trim()).filter(Boolean) : [];

    const ownedRaw = document.getElementById("owned-input").value;
    const alreadyOwned = ownedRaw ? ownedRaw.split(",").map(s => s.trim()).filter(Boolean) : [];

    const payload = {
      occasion: occasion,
      recipient: recipient,
      relationship: relationship,
      budget_min: budgetMin,
      budget_max: budgetMax,
      interests: selectedInterests,
      preferences: selectedPreferences,
      disliked_items: dislikedItems,
      already_owned: alreadyOwned,
      gift_type: giftType,
      preferred_style: document.getElementById("style-input").value.trim(),
      age_range: document.getElementById("age-input").value.trim(),
      optional_notes: document.getElementById("notes-input").value.trim()
    };

    // Show loading
    showLoading("Executing LangGraph Decision Pipeline...");

    try {
      const response = await fetch("/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Decision workflow failed.");
      }

      const data = await response.json();
      renderResults(data);
    } catch (err) {
      alert("Error: " + err.message);
      showEmptyState();
    } finally {
      hideLoading();
    }
  });

  // State Transition Helpers
  function showLoading(message) {
    if (loadingStageTitle) loadingStageTitle.textContent = message;
    stateEmpty.classList.add("hidden");
    stateResults.classList.add("hidden");
    stateLoading.classList.remove("hidden");
    btnSubmit.disabled = true;
  }

  function hideLoading() {
    btnSubmit.disabled = false;
    stateLoading.classList.add("hidden");
  }

  function showEmptyState() {
    stateLoading.classList.add("hidden");
    stateResults.classList.add("hidden");
    stateEmpty.classList.remove("hidden");
  }

  // 7. Render Recommendation Results
  function renderResults(data) {
    currentSessionId = data.session_id;

    document.getElementById("display-session-id").textContent = currentSessionId ? currentSessionId.slice(0, 13) + "..." : "Active";
    
    const enginePill = document.getElementById("display-engine-pill");
    if (data.mode === "gemini") {
      enginePill.textContent = "Gemini AI Reasoning";
      enginePill.style.background = "#EFF6FF";
      enginePill.style.color = "#1D4ED8";
    } else {
      enginePill.textContent = "Deterministic Algorithmic Engine";
      enginePill.style.background = "#FAF5FF";
      enginePill.style.color = "#6B21A8";
    }

    const selected = data.selected_gift;
    if (!selected) {
      alert(data.decision_explanation || "No candidates survived constraints.");
      showEmptyState();
      return;
    }

    // Top Candidate
    document.getElementById("best-category").textContent = selected.gift_category || "Keepsake";
    document.getElementById("best-name").textContent = selected.gift_name;
    document.getElementById("best-total-score").textContent = Math.round(selected.total_score);

    const costMin = Math.round(selected.estimated_cost_min || 0);
    const costMax = Math.round(selected.estimated_cost_max || costMin);
    document.getElementById("best-cost-range").textContent = costMin === costMax ? `₹${costMin.toLocaleString()}` : `₹${costMin.toLocaleString()} – ₹${costMax.toLocaleString()}`;

    const statusPill = document.getElementById("best-budget-status");
    statusPill.textContent = selected.budget_fit_status || "Within Budget";

    document.getElementById("best-desc").textContent = selected.description || "";
    document.getElementById("best-why").textContent = selected.why_it_matches || "";

    // Positive factors
    const posList = document.getElementById("best-positives");
    posList.innerHTML = "";
    (selected.positive_factors || []).forEach(f => {
      const li = document.createElement("li");
      li.textContent = f;
      posList.appendChild(li);
    });

    // Drawbacks
    const tradeList = document.getElementById("best-tradeoffs");
    tradeList.innerHTML = "";
    (selected.trade_offs || []).forEach(t => {
      const li = document.createElement("li");
      li.textContent = t;
      tradeList.appendChild(li);
    });

    // Personalization note
    const persWrap = document.getElementById("best-pers-wrap");
    if (selected.personalization_possibilities) {
      persWrap.style.display = "block";
      document.getElementById("best-personalization").textContent = selected.personalization_possibilities;
    } else {
      persWrap.style.display = "none";
    }

    // Score Breakdown Bars
    const breakdown = selected.score_breakdown || {};
    updateScoreBar("interest", breakdown.interest_match_score || 0, 30);
    updateScoreBar("budget", breakdown.budget_fit_score || 0, 25);
    updateScoreBar("relevance", breakdown.relevance_score || 0, 20);
    updateScoreBar("purpose", breakdown.purpose_match_score || 0, 15);
    updateScoreBar("personalization", breakdown.personalization_score || 0, 10);

    // Alternatives
    renderAlternatives(data.alternatives || []);

    // Full Decision Rationale Markdown Rendering
    renderMarkdownRationale(data.decision_explanation || "");

    // Refinement History
    renderHistory(data.feedback_history || []);

    stateResults.classList.remove("hidden");
    stateResults.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function updateScoreBar(key, awarded, max) {
    const scoreEl = document.getElementById(`score-${key}`);
    const barEl = document.getElementById(`bar-${key}`);
    if (scoreEl && barEl) {
      scoreEl.textContent = `${awarded.toFixed(1)} / ${max} pts`;
      const pct = Math.min(100, Math.max(5, (awarded / max) * 100));
      barEl.style.width = `${pct}%`;
    }
  }

  function renderAlternatives(alternatives) {
    const grid = document.getElementById("alternatives-grid");
    grid.innerHTML = "";

    if (alternatives.length === 0) {
      grid.innerHTML = "<p class='card-desc'>No close alternatives within the exact budget bracket.</p>";
      return;
    }

    alternatives.forEach(alt => {
      const card = document.createElement("div");
      card.className = "alt-card";

      const aMin = Math.round(alt.estimated_cost_min || 0);
      const aMax = Math.round(alt.estimated_cost_max || aMin);
      const priceText = aMin === aMax ? `₹${aMin.toLocaleString()}` : `₹${aMin.toLocaleString()}–₹${aMax.toLocaleString()}`;

      const tradeText = (alt.trade_offs && alt.trade_offs.length > 0) ? alt.trade_offs[0] : "Alternative option";

      card.innerHTML = `
        <div class="alt-header">
          <span class="alt-cat">${escapeHtml(alt.gift_category || "")}</span>
          <span class="alt-score">Score: ${Math.round(alt.total_score)}/100</span>
        </div>
        <h4 class="alt-name">${escapeHtml(alt.gift_name)}</h4>
        <span class="alt-cost">${priceText}</span>
        <p class="alt-desc">${escapeHtml(alt.description || "")}</p>
        <span class="alt-tradeoff">${escapeHtml(tradeText)}</span>
      `;
      grid.appendChild(card);
    });
  }

  function renderMarkdownRationale(markdownText) {
    const container = document.getElementById("decision-explanation-body");
    // Simple, safe parser for common markdown elements
    let html = markdownText
      .replace(/^### (.*$)/gim, '<h4>$1</h4>')
      .replace(/^## (.*$)/gim, '<h3>$1</h3>')
      .replace(/\*\*(.*?)\*\*/gim, '<b>$1</b>')
      .replace(/\*(.*?)\*/gim, '<i>$1</i>')
      .replace(/^\• (.*$)/gim, '<li>$1</li>')
      .replace(/^\* (.*$)/gim, '<li>$1</li>')
      .replace(/\n\n/gim, '</p><p>');

    if (html.includes('<li>')) {
      html = html.replace(/(<li>.*<\/li>)/gms, '<ul>$1</ul>');
    }
    container.innerHTML = `<p>${html}</p>`;
  }

  function renderHistory(history) {
    const histSection = document.getElementById("history-section");
    const histList = document.getElementById("history-list");
    if (!history || history.length === 0) {
      histSection.style.display = "none";
      return;
    }

    histSection.style.display = "block";
    histList.innerHTML = "";
    history.forEach((item, index) => {
      const li = document.createElement("li");
      li.className = "history-item";
      li.innerHTML = `<strong>Iteration ${index + 1}:</strong> Feedback: <i>"${escapeHtml(item.reason)}"</i> ${item.custom_feedback ? `— Note: "${escapeHtml(item.custom_feedback)}"` : ''}`;
      histList.appendChild(li);
    });
  }

  // 8. Feedback Handling
  async function submitFeedback(reason, customNote = "") {
    if (!currentSessionId) return;

    showLoading(`Adapting to Feedback: "${reason}"...`);

    try {
      const res = await fetch(`/recommend/${currentSessionId}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          reason: reason,
          custom_feedback: customNote,
          rejected_gift_name: document.getElementById("best-name").textContent
        })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Feedback adaptation failed.");
      }

      const updatedData = await res.json();
      renderResults(updatedData);
    } catch (err) {
      alert("Feedback failed: " + err.message);
    } finally {
      hideLoading();
    }
  }

  document.querySelectorAll(".btn-feedback").forEach(btn => {
    btn.addEventListener("click", () => {
      submitFeedback(btn.dataset.reason);
    });
  });

  const customFeedbackInput = document.getElementById("custom-feedback-input");
  document.getElementById("btn-submit-custom-feedback").addEventListener("click", () => {
    const note = customFeedbackInput.value.trim();
    if (note) {
      submitFeedback("Custom Refinement", note);
      customFeedbackInput.value = "";
    }
  });

  // 9. Download PDF Report
  btnDownloadPdf.addEventListener("click", () => {
    if (!currentSessionId) return;
    window.location.href = `/recommend/${currentSessionId}/report`;
  });

  // 10. Workflow Modal
  btnViewWorkflow.addEventListener("click", () => {
    workflowModal.classList.remove("hidden");
  });

  btnCloseModal.addEventListener("click", () => {
    workflowModal.classList.add("hidden");
  });

  workflowModal.addEventListener("click", (e) => {
    if (e.target === workflowModal) {
      workflowModal.classList.add("hidden");
    }
  });

  workflowTabs.forEach(tab => {
    tab.addEventListener("click", () => {
      workflowTabs.forEach(t => t.classList.remove("active"));
      tab.classList.add("active");
      document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
      document.getElementById(tab.dataset.tab).classList.add("active");
    });
  });

  function escapeHtml(str) {
    if (!str) return "";
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
});
