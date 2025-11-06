const storageKey = "jizhang-transactions";
const form = document.querySelector("#transaction-form");
const tableBody = document.querySelector("#transaction-table");
const emptyState = document.querySelector("#empty-state");
const totalIncomeEl = document.querySelector("#total-income");
const totalExpenseEl = document.querySelector("#total-expense");
const balanceEl = document.querySelector("#balance");
const downloadBtn = document.querySelector("#download");
const importInput = document.querySelector("#import");
const clearAllBtn = document.querySelector("#clear-all");
const filterCategory = document.querySelector("#filter-category");
const filterFrom = document.querySelector("#filter-from");
const filterTo = document.querySelector("#filter-to");
const resetFilters = document.querySelector("#reset-filters");

let transactions = loadTransactions();

function loadTransactions() {
  try {
    const saved = localStorage.getItem(storageKey);
    if (!saved) return [];
    const parsed = JSON.parse(saved);
    if (!Array.isArray(parsed)) return [];
    return parsed.map((item) => ({
      ...item,
      date: item.date ?? new Date().toISOString().slice(0, 10),
    }));
  } catch (error) {
    console.error("读取本地数据失败", error);
    return [];
  }
}

function persist() {
  localStorage.setItem(storageKey, JSON.stringify(transactions));
}

function render() {
  const filters = {
    category: filterCategory.value.trim().toLowerCase(),
    from: filterFrom.value ? new Date(filterFrom.value) : null,
    to: filterTo.value ? new Date(filterTo.value) : null,
  };

  const filtered = transactions.filter((transaction) => {
    const matchesCategory = filters.category
      ? transaction.category.toLowerCase().includes(filters.category)
      : true;

    const date = new Date(transaction.date);
    const matchesFrom = filters.from ? date >= filters.from : true;
    const matchesTo = filters.to ? date <= filters.to : true;

    return matchesCategory && matchesFrom && matchesTo;
  });

  tableBody.innerHTML = "";

  if (filtered.length === 0) {
    emptyState.hidden = false;
  } else {
    emptyState.hidden = true;
    const rows = filtered
      .sort((a, b) => new Date(b.date) - new Date(a.date))
      .map((transaction) => {
        const row = document.createElement("tr");
        row.innerHTML = `
          <td>${transaction.date}</td>
          <td>${transaction.type === "income" ? "收入" : "支出"}</td>
          <td>${escapeHtml(transaction.category)}</td>
          <td class="amount">${formatCurrency(transaction.amount)}</td>
          <td>${escapeHtml(transaction.note || "-")}</td>
          <td><button class="delete" data-id="${transaction.id}">删除</button></td>
        `;
        return row;
      });

    rows.forEach((row) => tableBody.appendChild(row));
  }

  const income = transactions
    .filter((item) => item.type === "income")
    .reduce((sum, item) => sum + Number(item.amount), 0);
  const expense = transactions
    .filter((item) => item.type === "expense")
    .reduce((sum, item) => sum + Number(item.amount), 0);

  totalIncomeEl.textContent = formatCurrency(income);
  totalExpenseEl.textContent = formatCurrency(expense);
  balanceEl.textContent = formatCurrency(income - expense);
}

function formatCurrency(amount) {
  return `¥${Number(amount).toFixed(2)}`;
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function clearForm() {
  form.reset();
  document.querySelector("#type").value = "expense";
  document.querySelector("#date").value = new Date()
    .toISOString()
    .slice(0, 10);
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const amount = Number(document.querySelector("#amount").value);
  if (!Number.isFinite(amount) || amount <= 0) {
    alert("请输入大于 0 的金额");
    return;
  }

  const transaction = {
    id: crypto.randomUUID(),
    type: document.querySelector("#type").value,
    amount,
    category: document.querySelector("#category").value.trim() || "未分类",
    date:
      document.querySelector("#date").value ||
      new Date().toISOString().slice(0, 10),
    note: document.querySelector("#note").value.trim(),
  };

  transactions.push(transaction);
  persist();
  render();
  clearForm();
});

tableBody.addEventListener("click", (event) => {
  const button = event.target.closest("button.delete");
  if (!button) return;

  const id = button.dataset.id;
  transactions = transactions.filter((transaction) => transaction.id !== id);
  persist();
  render();
});

downloadBtn.addEventListener("click", () => {
  const blob = new Blob([JSON.stringify(transactions, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `jizhang-${new Date().toISOString().slice(0, 10)}.json`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
});

importInput.addEventListener("change", (event) => {
  const file = event.target.files?.[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = () => {
    try {
      const parsed = JSON.parse(reader.result);
      if (!Array.isArray(parsed)) {
        throw new Error("格式错误");
      }
      transactions = parsed.map((item) => ({
        id: item.id || crypto.randomUUID(),
        type: item.type === "income" ? "income" : "expense",
        amount: Number(item.amount) || 0,
        category: item.category ? String(item.category) : "未分类",
        date: item.date || new Date().toISOString().slice(0, 10),
        note: item.note ? String(item.note) : "",
      }));
      persist();
      render();
      alert("数据导入成功");
    } catch (error) {
      alert("导入失败，请确认文件格式正确");
      console.error("导入失败", error);
    } finally {
      importInput.value = "";
    }
  };
  reader.readAsText(file);
});

clearAllBtn.addEventListener("click", () => {
  if (!confirm("确定要清空所有账目吗？此操作不可撤销。")) {
    return;
  }
  transactions = [];
  persist();
  render();
});

[filterCategory, filterFrom, filterTo].forEach((input) =>
  input.addEventListener("input", render)
);

resetFilters.addEventListener("click", () => {
  filterCategory.value = "";
  filterFrom.value = "";
  filterTo.value = "";
  render();
});

if (transactions.length === 0) {
  document.querySelector("#date").value = new Date()
    .toISOString()
    .slice(0, 10);
}

render();
