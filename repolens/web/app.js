const $ = (selector) => document.querySelector(selector);

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
  show(output, "Indexing...");
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
  show(output, "Thinking...");
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
  show(output, "Reviewing...");
  try {
    const data = await postJson("/api/review", { diff: $("#diff").value });
    show(output, data);
  } catch (error) {
    show(output, error.message);
  }
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
