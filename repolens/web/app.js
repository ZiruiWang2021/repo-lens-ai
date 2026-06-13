const $ = (selector) => document.querySelector(selector);

const translations = {
  en: {
    title: "Codebase Agent Workbench",
    status: "demo provider",
    sourceLabel: "Repository path or GitHub URL",
    indexButton: "Index",
    questionLabel: "Question",
    askButton: "Ask",
    diffLabel: "Unified diff",
    reviewButton: "Review",
    langToggle: "中文",
    indexing: "Indexing...",
    thinking: "Thinking...",
    reviewing: "Reviewing...",
    defaultQuestion: "Where is prompt injection handled?",
  },
  zh: {
    title: "代码库智能体工作台",
    status: "演示模型，无需 API Key",
    sourceLabel: "仓库路径或 GitHub URL",
    indexButton: "索引",
    questionLabel: "代码问题",
    askButton: "提问",
    diffLabel: "统一 diff",
    reviewButton: "审查",
    langToggle: "English",
    indexing: "正在索引...",
    thinking: "正在分析...",
    reviewing: "正在审查...",
    defaultQuestion: "Prompt 注入防护在哪里处理？",
  },
};

let locale =
  localStorage.getItem("repolens-locale") ||
  (navigator.language && navigator.language.toLowerCase().startsWith("zh") ? "zh" : "en");

function t(key) {
  return translations[locale][key];
}

function applyLocale() {
  document.documentElement.lang = locale === "zh" ? "zh-CN" : "en";
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    node.textContent = t(node.dataset.i18n);
  });
  $("#lang-toggle").textContent = t("langToggle");
  if (!$("#question").dataset.touched) {
    $("#question").value = t("defaultQuestion");
  }
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Request failed");
  }
  return data;
}

function show(target, value) {
  target.textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

$("#index-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const output = $("#index-output");
  show(output, t("indexing"));
  try {
    const data = await postJson("/api/repos/index", { source: $("#source").value });
    show(output, data);
  } catch (error) {
    show(output, error.message);
  }
});

$("#ask-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const output = $("#answer-output");
  show(output, t("thinking"));
  try {
    const data = await postJson("/api/chat", { question: $("#question").value });
    show(output, data);
  } catch (error) {
    show(output, error.message);
  }
});

$("#review-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const output = $("#review-output");
  show(output, t("reviewing"));
  try {
    const data = await postJson("/api/review", { diff: $("#diff").value });
    show(output, data);
  } catch (error) {
    show(output, error.message);
  }
});

$("#lang-toggle").addEventListener("click", () => {
  locale = locale === "zh" ? "en" : "zh";
  localStorage.setItem("repolens-locale", locale);
  applyLocale();
});

$("#question").addEventListener("input", () => {
  $("#question").dataset.touched = "true";
});

$("#diff").value = `diff --git a/app.py b/app.py
index 2f4a111..91bf223 100644
--- a/app.py
+++ b/app.py
@@ -18,3 +18,8 @@ def render_receipt(invoice: Invoice) -> str:
     total = calculate_total(invoice)
     return f"Total due: {total} cents"
+
+
+def run_admin_expression(expression: str) -> object:
+    api_key = "sk-demo-hardcoded-secret"
+    return eval(expression)`;

applyLocale();
