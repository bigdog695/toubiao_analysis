const state = {
  tenderReady: false,
  bidReady: false,
};

const statusTenderEl = document.getElementById("status-tender");
const statusBidEl = document.getElementById("status-bid");
const statusRunEl = document.getElementById("status-run");
const resultEl = document.getElementById("result");

const btnUploadTender = document.getElementById("btn-upload-tender");
const btnUploadBid = document.getElementById("btn-upload-bid");
const btnRunScore = document.getElementById("btn-run-score");

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function statusType(text) {
  const raw = String(text || "");
  if (raw.includes("失败")) return "fail";
  if (raw.includes("不通过")) return "fail";
  if (raw.includes("已就绪") || raw.includes("已完成")) return "pass";
  if (raw.includes("未就绪") || raw.includes("待执行")) return "pending";
  if (raw.includes("通过")) return "pass";
  if (raw.includes("待补充")) return "pending";
  return "neutral";
}

function setTag(el, text) {
  const type = statusType(text);
  el.className = `tag tag-${type}`;
  el.textContent = text;
}

async function callApi(url) {
  const resp = await fetch(url, { method: "POST" });
  if (!resp.ok) {
    throw new Error(`请求失败: ${resp.status}`);
  }
  return resp.json();
}

function renderList(items) {
  if (!items || !items.length) {
    return "<p class=\"item-reason\">暂无</p>";
  }
  const lis = items.map((x) => `<li>${escapeHtml(x)}</li>`).join("");
  return `<ul class=\"summary-list\">${lis}</ul>`;
}

function renderCheckCards(items) {
  return items
    .map((item) => {
      const status = item.status || "待补充";
      const detail = item.detail || "";
      return `
        <article class="item-card">
          <div class="item-top">
            <h4 class="item-title">${escapeHtml(item.name || "未命名")}</h4>
            <span class="tag tag-${statusType(status)}">${escapeHtml(status)}</span>
          </div>
          <p class="item-reason">${escapeHtml(detail)}</p>
        </article>
      `;
    })
    .join("");
}

function scoreText(item) {
  const score = item.score;
  const max = item.max_score;
  if (typeof score === "number" && typeof max === "number") {
    return `${score.toFixed(2)} / ${max.toFixed(1)}`;
  }
  if (score !== undefined && score !== null && String(score).trim() !== "") {
    return escapeHtml(score);
  }
  if (typeof max === "number") {
    return `-- / ${max.toFixed(1)}`;
  }
  return "--";
}

function renderEvidence(evidence) {
  if (!evidence) return "";
  const list = Array.isArray(evidence) ? evidence : [evidence];
  const valid = list.filter((x) => String(x || "").trim());
  if (!valid.length) return "";
  const lis = valid.map((ev) => `<li>${escapeHtml(ev)}</li>`).join("");
  return `<ul class="evidence-list">${lis}</ul>`;
}

function renderScoreCards(items) {
  return items
    .map((item) => {
      const result = item.result || "待补充";
      const confidence =
        typeof item.confidence === "number"
          ? `${(item.confidence * 100).toFixed(1)}%`
          : String(item.confidence || "").trim();
      const reason = item.reason || "";
      return `
        <article class="item-card">
          <div class="item-top">
            <h4 class="item-title">${escapeHtml(item.item_name || item.name || "未命名评分项")}</h4>
            <span class="tag tag-${statusType(result)}">${escapeHtml(result)}</span>
          </div>
          <p class="item-score">实得分 / 满分：${scoreText(item)}</p>
          <div class="item-meta">
            ${confidence ? `<span class="meta-pill">置信度：${escapeHtml(confidence)}</span>` : ""}
            ${item.manual_review_required ? `<span class="meta-pill">待人工复核</span>` : ""}
          </div>
          ${reason ? `<p class="item-reason">理由：${escapeHtml(reason)}</p>` : ""}
          ${renderEvidence(item.evidence)}
        </article>
      `;
    })
    .join("");
}

function renderSummary(summary) {
  return `
    <div class="item-grid">
      <article class="item-card"><h4 class="item-title">资格核验结论</h4><p class="item-score"><span class="tag tag-${statusType(summary.qualification_result)}">${escapeHtml(summary.qualification_result || "待补充")}</span></p></article>
      <article class="item-card"><h4 class="item-title">商务评分</h4><p class="item-score">${escapeHtml(summary.business_score || "--")}</p></article>
      <article class="item-card"><h4 class="item-title">技术评分（扣分前）</h4><p class="item-score">${escapeHtml(summary.technical_score_before_penalty || "--")}</p></article>
      <article class="item-card"><h4 class="item-title">技术文件格式扣分</h4><p class="item-score">${escapeHtml(summary.technical_penalty || "--")}</p></article>
      <article class="item-card"><h4 class="item-title">技术评分（最终）</h4><p class="item-score">${escapeHtml(summary.technical_score_final || "--")}</p></article>
      <article class="item-card"><h4 class="item-title">报价评分</h4><p class="item-score">${escapeHtml(summary.price_score || "--")}</p></article>
    </div>
    <h4 style="margin:12px 0 8px;">待人工复核项</h4>
    ${renderList(summary.manual_review_items || [])}
  `;
}

function highlightCard(title, items, type) {
  const data = items && items.length ? items : ["暂无"];
  const lis = data.map((x) => `<li>${escapeHtml(x)}</li>`).join("");
  return `
    <article class="highlight-card">
      <h4>${escapeHtml(title)}</h4>
      <ul>${lis}</ul>
    </article>
  `;
}

function renderResult(data) {
  const checkResult = data.check_result || {};
  const scoreSummary = data.score_summary || {};
  const insights = data.insights || {};

  resultEl.innerHTML = `
    <section class="card overview">
      <div class="overview-info">
        <p><strong>投标文件：</strong>${escapeHtml(data.bid_file_name || "--")}</p>
        <p><strong>投标单位：</strong>${escapeHtml(data.bidder_name || "--")}</p>
        <p><strong>项目名称：</strong>${escapeHtml(data.project_name || "--")}</p>
        <p><strong>招标模型状态：</strong>${escapeHtml(data.tender_model_status || "--")}</p>
      </div>
      <div class="overview-score">
        <div class="total-label">总分（满分 100）</div>
        <div class="total-score">${escapeHtml(scoreSummary.total_score_value ?? "--")}</div>
        <div>${escapeHtml(scoreSummary.total_score || "")}</div>
      </div>
    </section>

    <section class="card section">
      <h3>文件检查结果</h3>
      <div class="item-grid">${renderCheckCards(checkResult.file_structure_check || [])}</div>
    </section>

    <section class="card section">
      <h3>格式与人工复核结果</h3>
      <div class="item-grid">${renderCheckCards(checkResult.format_and_manual_review || [])}</div>
    </section>

    <section class="card section">
      <h3>资格与证书核验结果</h3>
      <div class="item-grid">${renderCheckCards(data.qualification_check || [])}</div>
    </section>

    <section class="card section">
      <h3>商务评分结果</h3>
      <div class="item-grid">${renderScoreCards(data.business_scoring || [])}</div>
    </section>

    <section class="card section">
      <h3>技术评分结果</h3>
      <div class="item-grid">${renderScoreCards(data.technical_scoring || [])}</div>
    </section>

    <section class="card section">
      <h3>技术文件格式扣分</h3>
      <div class="item-grid">${renderScoreCards(data.technical_penalty || [])}</div>
    </section>

    <section class="card section">
      <h3>报价评分结果</h3>
      <div class="item-grid">${renderScoreCards([data.price_scoring || {}])}</div>
    </section>

    <section class="card section">
      <h3>总分汇总</h3>
      ${renderSummary(scoreSummary)}
    </section>

    <section class="card section">
      <h3>重点提示</h3>
      <div class="highlight-grid">
        ${highlightCard("高分项", insights.high_score_items || [], "pass")}
        ${highlightCard("风险项", insights.risk_items || [], "fail")}
        ${highlightCard("待人工复核项", insights.manual_review_items || [], "pending")}
      </div>
    </section>
  `;
}

async function withRunStatus(work) {
  try {
    setTag(statusRunEl, "执行中");
    await work();
    setTag(statusRunEl, "已完成");
  } catch (err) {
    setTag(statusRunEl, "执行失败");
    resultEl.innerHTML = `<article class="card"><h2>执行失败</h2><p>${escapeHtml(err.message || err)}</p></article>`;
  }
}

btnUploadTender.addEventListener("click", async () => {
  btnUploadTender.disabled = true;
  try {
    const data = await callApi("/mock-upload-tender");
    state.tenderReady = true;
    setTag(statusTenderEl, data.message || "招标文件已就绪（本地读取）");
  } catch (err) {
    setTag(statusTenderEl, "未就绪");
  } finally {
    btnUploadTender.disabled = false;
  }
});

btnUploadBid.addEventListener("click", async () => {
  btnUploadBid.disabled = true;
  try {
    const data = await callApi("/mock-upload-bid");
    state.bidReady = true;
    setTag(statusBidEl, data.message || "投标文件已就绪（本地读取）");
  } catch (err) {
    setTag(statusBidEl, "未就绪");
  } finally {
    btnUploadBid.disabled = false;
  }
});

btnRunScore.addEventListener("click", async () => {
  btnRunScore.disabled = true;
  await withRunStatus(async () => {
    const resp = await callApi("/run-score");
    if (!resp.ok) {
      throw new Error(resp.message || "打分失败");
    }
    renderResult(resp.data || {});
  });
  btnRunScore.disabled = false;
});
