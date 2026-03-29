const state = {
  config: null,
  currentStep: 1,
  session: null,
  selectedModality: null,
  selectedModules: [],
  uploadedFiles: [],
  pollTimer: null,
  previewMode: false,
  activeGalleryIndex: 0,
};

const nodes = {
  stages: document.querySelectorAll(".stage"),
  stepperItems: document.querySelectorAll(".stepper li"),
  modalityGrid: document.getElementById("modalityGrid"),
  fileInput: document.getElementById("fileInput"),
  dropzone: document.getElementById("dropzone"),
  dropzoneHint: document.getElementById("dropzoneHint"),
  fileList: document.getElementById("fileList"),
  fileCounter: document.getElementById("fileCounter"),
  featureList: document.getElementById("featureList"),
  analysisSummary: document.getElementById("analysisSummary"),
  analysisHighlights: document.getElementById("analysisHighlights"),
  summaryBadge: document.getElementById("summaryBadge"),
  galleryGrid: document.getElementById("galleryGrid"),
  galleryCounter: document.getElementById("galleryCounter"),
  lightbox: document.getElementById("lightbox"),
  lightboxImage: document.getElementById("lightboxImage"),
  lightboxCaption: document.getElementById("lightboxCaption"),
  lightboxClose: document.getElementById("lightboxClose"),
  sessionBadge: document.getElementById("sessionBadge"),
  sessionSummary: document.getElementById("sessionSummary"),
  runStatusPill: document.getElementById("runStatusPill"),
  runStatusText: document.getElementById("runStatusText"),
  toast: document.getElementById("toast"),
  loginNextBtn: document.getElementById("loginNextBtn"),
  uploadNextBtn: document.getElementById("uploadNextBtn"),
  runAnalysisBtn: document.getElementById("runAnalysisBtn"),
  restartBtn: document.getElementById("restartBtn"),
};

function showToast(message) {
  nodes.toast.textContent = message;
  nodes.toast.classList.add("show");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => {
    nodes.toast.classList.remove("show");
  }, 2600);
}

function openLightbox(item) {
  if (!item) {
    return;
  }
  nodes.lightbox.hidden = false;
  nodes.lightboxImage.src = item.url;
  nodes.lightboxImage.alt = item.name;
  nodes.lightboxCaption.textContent = item.name;
  document.body.classList.add("lightbox-open");
}

function closeLightbox() {
  nodes.lightbox.hidden = true;
  nodes.lightboxImage.src = "";
  nodes.lightboxImage.alt = "";
  nodes.lightboxCaption.textContent = "";
  document.body.classList.remove("lightbox-open");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function localizeImageName(value) {
  let text = String(value ?? "");
  const replacements = [
    [/frontend run/gi, ""],
    [/R_BB|R BB/gi, "右臂肱二头肌"],
    [/L_BB|L BB/gi, "左臂肱二头肌"],
    [/eeg_mean|eeg mean/gi, "脑电平均通道"],
    [/\bRA\b/gi, "右上肢导联"],
    [/\bLA\b/gi, "左上肢导联"],
    [/\bV3\b/g, "V3导联"],
    [/\bV5\b/g, "V5导联"],
    [/\bF\b/g, "F导联"],
    [/filtered dataset/gi, "分析结果"],
    [/filtered signal/gi, "滤波后信号"],
    [/band power/gi, "频带功率图"],
    [/indices/gi, "指标图"],
    [/fft spectrum/gi, "FFT频谱图"],
    [/spectrogram/gi, "时频谱图"],
    [/rms and mdf/gi, "RMS与MDF分析图"],
    [/rms mdf/gi, "RMS与MDF分析图"],
    [/spectrum/gi, "频谱图"],
    [/trend/gi, "趋势图"],
    [/segment[_ ](\d+)/gi, "第$1段"],
    [/_/g, " "],
  ];
  replacements.forEach(([pattern, replacement]) => {
    text = text.replace(pattern, replacement);
  });
  return text.replace(/\s+/g, " ").trim();
}

function setStep(step) {
  state.currentStep = step;
  nodes.stages.forEach((stage) => {
    stage.classList.toggle("active", Number(stage.dataset.stage) === step);
  });
  nodes.stepperItems.forEach((item) => {
    item.classList.toggle("active", Number(item.dataset.step) === step);
  });
}

function getPreviewSettings() {
  const query = new URLSearchParams(window.location.search);
  const preview = query.get("preview");
  if (!preview) {
    return null;
  }
  return {
    step: Number(preview.replace(/[^\d]/g, "")) || 1,
    modality: query.get("modality") || "emg",
  };
}

function updateSummary() {
  const values = {
    name: state.session?.user?.name || "未填写",
    gender: state.session?.user?.gender || "未填写",
    age: state.session?.user?.age || "未填写",
    modality: state.selectedModality ? state.config.modalities[state.selectedModality].label : "未选择",
    files: `${state.uploadedFiles.length || 0} 个`,
  };

  const fields = Object.values(values);
  [...nodes.sessionSummary.querySelectorAll("dd")].forEach((node, index) => {
    node.textContent = fields[index];
  });

  const status = state.session?.status || "draft";
  const map = {
    draft: "未开始",
    uploaded: "已上传",
    running: "运行中",
    completed: "已完成",
    error: "异常",
  };
  nodes.sessionBadge.textContent = map[status] || "进行中";
}

function renderModalities() {
  nodes.modalityGrid.innerHTML = "";
  Object.entries(state.config.modalities).forEach(([key, meta]) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "modality-card";
    button.innerHTML = `
      <h3>${meta.label}</h3>
      <p>${meta.description}</p>
      <span class="meta-chip">${meta.channel_hint}</span>
    `;
    button.addEventListener("click", () => {
      state.selectedModality = key;
      state.selectedModules = meta.modules.map((item) => item.key);
      state.uploadedFiles = [];
      renderModalities();
      renderFiles();
      renderFeatures();
      nodes.uploadNextBtn.disabled = true;
      nodes.dropzoneHint.textContent = meta.channel_hint;
      updateSummary();
    });

    if (state.selectedModality === key) {
      button.classList.add("selected");
    }
    nodes.modalityGrid.appendChild(button);
  });
}

function renderFiles() {
  if (!state.uploadedFiles.length) {
    nodes.fileList.className = "file-list empty";
    nodes.fileList.innerHTML = "<li>尚未上传文件</li>";
    nodes.fileCounter.textContent = "0 个文件";
    return;
  }

  nodes.fileList.className = "file-list";
  nodes.fileList.innerHTML = state.uploadedFiles
    .map((file) => `<li>${file.name}</li>`)
    .join("");
  nodes.fileCounter.textContent = `${state.uploadedFiles.length} 个文件`;
}

function renderFeatures() {
  if (!state.selectedModality) {
    nodes.featureList.innerHTML = "";
    return;
  }
  const features = state.config.modalities[state.selectedModality].modules;
  const selectedSet = new Set(state.selectedModules);
  nodes.featureList.innerHTML = features
    .map(
      (feature) => `
      <button
        type="button"
        class="feature-card ${selectedSet.has(feature.key) ? "is-enabled" : "is-disabled"}"
        data-feature-key="${feature.key}"
        aria-pressed="${selectedSet.has(feature.key)}"
      >
        <div class="feature-card-top">
          <h3>${feature.label}</h3>
          <span class="feature-switch">${selectedSet.has(feature.key) ? "已开启" : "已关闭"}</span>
        </div>
        <p>${feature.detail}</p>
      </button>
    `,
    )
    .join("");

  nodes.featureList.querySelectorAll("[data-feature-key]").forEach((button) => {
    button.addEventListener("click", () => {
      const key = button.dataset.featureKey;
      if (!key) {
        return;
      }

      if (state.selectedModules.includes(key)) {
        state.selectedModules = state.selectedModules.filter((item) => item !== key);
      } else {
        state.selectedModules = [...state.selectedModules, key];
      }
      renderFeatures();
    });
  });
}

function setRunStatus(status, text) {
  nodes.runStatusPill.className = "run-pill";
  if (status) {
    nodes.runStatusPill.classList.add(status);
  }
  const textMap = {
    draft: "待运行",
    uploaded: "可开始",
    running: "运行中",
    completed: "已完成",
    error: "异常",
  };
  nodes.runStatusPill.textContent = textMap[status] || "处理中";
  nodes.runStatusText.textContent = text;
}

function renderGallery(items = []) {
  nodes.galleryCounter.textContent = `${items.length} 张图`;
  if (!items.length) {
    nodes.galleryGrid.className = "gallery-grid empty";
    nodes.galleryGrid.innerHTML = "<p>分析完成后将在这里展示结果图片。</p>";
    return;
  }

  nodes.galleryGrid.className = "gallery-grid";
  nodes.galleryGrid.innerHTML = items
    .map(
      (item, index) => `
      <figure
        class="gallery-item"
        data-gallery-index="${index}"
        role="button"
        tabindex="0"
        aria-label="${escapeHtml(localizeImageName(item.name))}"
      >
        <img src="${item.url}" alt="${escapeHtml(localizeImageName(item.name))}" />
        <figcaption>${escapeHtml(localizeImageName(item.name))}</figcaption>
      </figure>
    `,
    )
    .join("");

  nodes.galleryGrid.querySelectorAll("[data-gallery-index]").forEach((card) => {
    const openCurrent = () => {
      const index = Number(card.dataset.galleryIndex);
      const item = items[index];
      if (!item) {
        return;
      }
      openLightbox({ ...item, name: localizeImageName(item.name) });
    };

    card.addEventListener("click", openCurrent);
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        openCurrent();
      }
    });
  });
}

function parseSessionLog(log = "") {
  const info = {};
  const labels = [
    "Signal modality",
    "EDF files",
    "Band-pass",
    "Band-pass range",
    "Band-pass order",
    "Band-stop range",
    "Band-stop order",
    "Start time",
    "End time",
    "Duration",
    "Source channels",
    "Sampling rate",
    "Analysis channels",
    "ECG selected channel",
    "Segment count",
    "Segment labels",
  ];

  log.split(/\r?\n/).forEach((line) => {
    const trimmed = line.trim();
    labels.forEach((label) => {
      if (trimmed.startsWith(label)) {
        info[label] = trimmed.slice(label.length).trim();
      }
    });

    const sdnnMatch = trimmed.match(/SDNN\s+(.+)$/);
    if (sdnnMatch) {
      info.sdnn = sdnnMatch[1].trim();
    }

    const rmssdMatch = trimmed.match(/RMSSD\s+(.+)$/);
    if (rmssdMatch) {
      info.rmssd = rmssdMatch[1].trim();
    }
  });

  return info;
}

function setSummaryBadge(status) {
  nodes.summaryBadge.className = "summary-badge";
  const map = {
    draft: "待分析",
    uploaded: "可开始",
    running: "分析中",
    completed: "已生成摘要",
    error: "分析异常",
  };
  if (status) {
    nodes.summaryBadge.classList.add(status);
  }
  nodes.summaryBadge.textContent = map[status] || "处理中";
}

function renderAnalysisSummary(session = null) {
  const parsed = parseSessionLog(session?.log || "");
  const fallbackModality = state.selectedModality ? state.config.modalities[state.selectedModality].label : "待识别";
  const filterValue = [
    parsed["Band-pass range"] ? `带通 ${parsed["Band-pass range"]}` : parsed["Band-pass"] ? `带通 ${parsed["Band-pass"]}` : "",
    parsed["Band-pass order"] ? `阶数 ${parsed["Band-pass order"]}` : "",
  ]
    .filter(Boolean)
    .join(" | ");
  const notchValue = [
    parsed["Band-stop range"] ? `带阻 ${parsed["Band-stop range"]}` : "",
    parsed["Band-stop order"] ? `阶数 ${parsed["Band-stop order"]}` : "",
  ]
    .filter(Boolean)
    .join(" | ");
  const metrics = [
    { label: "信号类型", value: parsed["Signal modality"] || fallbackModality },
    { label: "采样率", value: parsed["Sampling rate"] || "待生成" },
    { label: "记录时长", value: parsed["Duration"] || "待生成" },
    { label: "原始通道", value: parsed["Source channels"] || "待解析" },
    { label: "分析通道", value: parsed["Analysis channels"] || "待解析" },
    { label: "带通滤波", value: filterValue || "待生成" },
    { label: "带阻滤波", value: notchValue || "待生成" },
    { label: "分段数量", value: parsed["Segment count"] || "待生成" },
  ];

  nodes.analysisSummary.innerHTML = metrics
    .map(
      (item) => `
      <article class="summary-tile">
        <span>${escapeHtml(item.label)}</span>
        <strong>${escapeHtml(item.value)}</strong>
      </article>
    `,
    )
    .join("");

  const selectedSet = new Set(state.selectedModules);
  const moduleLabels = state.selectedModality
    ? state.config.modalities[state.selectedModality].modules
        .filter((item) => selectedSet.has(item.key))
        .map((item) => item.label)
        .join("、") || "未选择"
    : "待确定";
  const fileLabel = parsed["EDF files"] || (state.uploadedFiles[0]?.name ?? "等待上传");
  const highlights = [
    `数据文件：${fileLabel}`,
    `已启用分析：${moduleLabels}`,
    parsed["Start time"] && parsed["End time"] ? `记录区间：${parsed["Start time"]} 至 ${parsed["End time"]}` : "",
    parsed["ECG selected channel"] ? `心电通道策略：${parsed["ECG selected channel"]}` : "",
    parsed.sdnn ? `SDNN：${parsed.sdnn}` : "",
    parsed.rmssd ? `RMSSD：${parsed.rmssd}` : "",
    session?.result_images?.length ? `结果图数量：${session.result_images.length} 张` : "",
  ].filter(Boolean);

  if (!highlights.length) {
    nodes.analysisHighlights.className = "analysis-highlight-list empty";
    nodes.analysisHighlights.innerHTML = "<p>分析完成后，这里会自动提炼关键结果信息。</p>";
    return;
  }

  nodes.analysisHighlights.className = "analysis-highlight-list";
  nodes.analysisHighlights.innerHTML = highlights
    .map((text) => `<div class="analysis-highlight">${escapeHtml(text)}</div>`)
    .join("");
}

function applyPreviewState() {
  const preview = getPreviewSettings();
  if (!preview || !state.config) {
    return false;
  }

  state.previewMode = true;
  state.selectedModality =
    preview.step >= 2 && preview.modality in state.config.modalities ? preview.modality : null;
  state.session = {
    id: "preview-session",
    status: preview.step >= 4 ? "completed" : preview.step >= 2 ? "uploaded" : "draft",
    user: {
      name: "张三",
      gender: "男",
      age: "29",
    },
    log: [
      "Signal modality          EMG (emg)",
      "EDF files                EMG_SIGNAL.edf",
      "Start time               2024-06-26 16:57:17.220",
      "End time                 2024-06-26 16:57:29.315",
      "Duration                 0:00:12.095000",
      "Source channels          R_BB",
      "Sampling rate            992.0000 Hz",
      "Analysis channels        R_BB",
      "Band-pass range          [20, 250]",
      "Band-pass order          4",
      "Band-stop range          [48, 52]",
      "Band-stop order          4",
      "Segment count            1",
    ].join("\n"),
  };

  document.getElementById("userName").value = state.session.user.name;
  document.getElementById("userGender").value = state.session.user.gender;
  document.getElementById("userAge").value = state.session.user.age;

  const previewFiles = {
    eeg: [{ name: "EEG_MULTI_CHANNEL.edf" }],
    ecg: [{ name: "ECG_MULTI_CHANNEL.edf" }],
    emg: [{ name: "EMG_SIGNAL.edf" }],
  };
  state.uploadedFiles = preview.step >= 2 && state.selectedModality ? previewFiles[state.selectedModality] : [];
  state.selectedModules = state.selectedModality ? state.config.modalities[state.selectedModality].modules.map((item) => item.key) : [];

  renderModalities();
  renderFiles();
  renderFeatures();
  updateSummary();

  nodes.dropzoneHint.textContent = state.selectedModality
    ? state.config.modalities[state.selectedModality].channel_hint
    : "请先选择模态";
  nodes.uploadNextBtn.disabled = preview.step < 2;

  if (preview.step >= 4) {
    state.session.result_images = [
      { name: "EMG 时频谱分析", url: "/preview-assets/图4_EMG时频谱分析.png" },
      { name: "EMG 频域指标分析", url: "/preview-assets/图5_EMG频域指标分析.png" },
    ];
    renderGallery([
      { name: "EMG 时频谱分析", url: "/preview-assets/图4_EMG时频谱分析.png" },
      { name: "EMG 频域指标分析", url: "/preview-assets/图5_EMG频域指标分析.png" },
    ]);
    setRunStatus("completed", "前端已汇总显示终端日志和分析结果图。");
  } else {
    renderGallery([]);
    setRunStatus(preview.step >= 2 ? "uploaded" : "draft", "此页面用于说明书截图预览。");
  }

  setSummaryBadge(state.session.status);
  renderAnalysisSummary(state.session);

  setStep(preview.step);
  return true;
}

async function fetchConfig() {
  const response = await fetch("/api/config");
  const payload = await response.json();
  state.config = payload;
  renderModalities();
}

async function createSession() {
  const name = document.getElementById("userName").value.trim();
  const gender = document.getElementById("userGender").value.trim();
  const age = document.getElementById("userAge").value.trim();

  if (!name || !gender || !age) {
    showToast("请完整填写姓名、性别和年龄。");
    return;
  }

  const response = await fetch("/api/session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, gender, age }),
  });
  const payload = await response.json();
  if (!payload.ok) {
    showToast(payload.error || "登录信息提交失败。");
    return;
  }

  state.session = payload.session;
  updateSummary();
  setStep(2);
  showToast("基础信息已记录。");
}

async function uploadFiles(files) {
  if (!state.session?.id) {
    showToast("请先完成登录信息填写。");
    return;
  }
  if (!state.selectedModality) {
    showToast("请先选择模态。");
    return;
  }
  if (!files.length) {
    return;
  }

  const formData = new FormData();
  formData.append("session_id", state.session.id);
  formData.append("modality", state.selectedModality);
  files.forEach((file) => formData.append("files", file));

  const response = await fetch("/api/upload", {
    method: "POST",
    body: formData,
  });
  const payload = await response.json();
  if (!payload.ok) {
    showToast(payload.error || "文件上传失败。");
    return;
  }

  state.session = payload.session;
  state.selectedModules = payload.session.modules ? [...payload.session.modules] : [];
  state.uploadedFiles = [...files];
  renderFiles();
  renderFeatures();
  updateSummary();
  nodes.uploadNextBtn.disabled = false;
  showToast("EDF 文件识别成功。");
}

async function startAnalysis() {
  if (!state.session?.id) {
    showToast("会话不存在，请重新开始。");
    return;
  }
  if (!state.selectedModules.length) {
    showToast("请至少保留一个分析模块。");
    return;
  }

  setStep(4);
  renderGallery([]);
  setRunStatus("running", "正在调用现有分析流程，请稍候。");
  setSummaryBadge("running");
  renderAnalysisSummary({
    status: "running",
    log: "",
    result_images: [],
  });

  const modules = [...state.selectedModules];
  const response = await fetch("/api/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: state.session.id, modules }),
  });
  const payload = await response.json();
  if (!payload.ok) {
    setRunStatus("error", payload.error || "分析启动失败。");
    showToast(payload.error || "分析启动失败。");
    return;
  }

  state.session = payload.session;
  updateSummary();
  pollSession();
  showToast("分析已启动。");
}

async function refreshSession() {
  if (!state.session?.id) {
    return;
  }
  const response = await fetch(`/api/session?id=${encodeURIComponent(state.session.id)}`);
  const payload = await response.json();
  if (!payload.ok) {
    showToast(payload.error || "会话刷新失败。");
    window.clearInterval(state.pollTimer);
    return;
  }

  state.session = payload.session;
  updateSummary();
  setSummaryBadge(state.session.status);
  renderAnalysisSummary(state.session);

  if (state.session.status === "running") {
    setRunStatus("running", "系统正在执行现有分析流程，日志会实时刷新。");
  } else if (state.session.status === "completed") {
    setRunStatus("completed", "分析完成，结果图已汇总展示。");
    renderGallery(state.session.result_images || []);
    window.clearInterval(state.pollTimer);
  } else if (state.session.status === "error") {
    setRunStatus("error", state.session.error || "分析出现异常。");
    renderGallery([]);
    window.clearInterval(state.pollTimer);
  }
}

function pollSession() {
  window.clearInterval(state.pollTimer);
  state.pollTimer = window.setInterval(refreshSession, 1200);
  refreshSession();
}

function resetApp() {
  window.clearInterval(state.pollTimer);
  state.session = null;
  state.selectedModality = null;
  state.selectedModules = [];
  state.uploadedFiles = [];
  state.activeGalleryIndex = 0;
  document.getElementById("loginForm").reset();
  nodes.uploadNextBtn.disabled = true;
  nodes.dropzoneHint.textContent = "请先选择模态";
  setRunStatus("draft", "点击“确定并开始分析”后，这里会显示实时状态。");
  setSummaryBadge("draft");
  renderGallery([]);
  renderAnalysisSummary();
  renderFiles();
  renderFeatures();
  renderModalities();
  updateSummary();
  setStep(1);
  showToast("已重置为新会话。");
}

function bindEvents() {
  if (state.previewMode) {
    document.querySelectorAll("button").forEach((button) => {
      button.disabled = true;
    });
    nodes.fileInput.disabled = true;
    return;
  }

  nodes.loginNextBtn.addEventListener("click", createSession);
  nodes.uploadNextBtn.addEventListener("click", () => {
    if (!state.uploadedFiles.length) {
      showToast("请先上传文件。");
      return;
    }
    renderFeatures();
    setStep(3);
  });
  nodes.runAnalysisBtn.addEventListener("click", startAnalysis);
  nodes.restartBtn.addEventListener("click", resetApp);
  nodes.lightboxClose.addEventListener("click", closeLightbox);
  nodes.lightbox.querySelectorAll("[data-lightbox-close]").forEach((node) => {
    node.addEventListener("click", closeLightbox);
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !nodes.lightbox.hidden) {
      closeLightbox();
    }
  });

  document.querySelectorAll("[data-back]").forEach((button) => {
    button.addEventListener("click", () => {
      setStep(Number(button.dataset.back));
    });
  });

  nodes.dropzone.addEventListener("click", () => {
    if (!state.selectedModality) {
      showToast("请先选择模态。");
      return;
    }
    nodes.fileInput.click();
  });

  nodes.fileInput.addEventListener("change", (event) => {
    uploadFiles([...event.target.files]);
  });

  ["dragenter", "dragover"].forEach((eventName) => {
    nodes.dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      if (!state.selectedModality) {
        return;
      }
      nodes.dropzone.classList.add("dragover");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    nodes.dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      nodes.dropzone.classList.remove("dragover");
    });
  });

  nodes.dropzone.addEventListener("drop", (event) => {
    if (!state.selectedModality) {
      showToast("请先选择模态。");
      return;
    }
    const files = [...event.dataTransfer.files];
    uploadFiles(files);
  });
}

async function bootstrap() {
  await fetchConfig();
  renderFiles();
  renderGallery([]);
  setRunStatus("draft", "点击“确定并开始分析”后，这里会显示实时状态。");
  setSummaryBadge("draft");
  updateSummary();
  renderAnalysisSummary();
  applyPreviewState();
  bindEvents();
}

bootstrap().catch((error) => {
  console.error(error);
  showToast("前端初始化失败，请刷新页面重试。");
});
