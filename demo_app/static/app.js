const loginPanel = document.querySelector("#login-panel");
const workspace = document.querySelector("#workspace");
const errorPanel = document.querySelector("#error");
const feedback = document.querySelector("#feedback");
const filter = document.querySelector("#status-filter");

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function api(path, method = "GET", payload) {
  const response = await fetch(path, {
    method,
    headers: payload === undefined ? {} : { "Content-Type": "application/json" },
    body: payload === undefined ? undefined : JSON.stringify(payload),
  });
  if (response.status === 204) return null;
  const result = await response.json();
  if (!response.ok) throw new ApiError(result.error.message, response.status);
  return result;
}

function showLogin() {
  workspace.hidden = true;
  loginPanel.hidden = false;
  document.querySelector("#orders").replaceChildren();
}

async function runAction(action) {
  errorPanel.hidden = true;
  feedback.textContent = "";
  try {
    await action();
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) showLogin();
    errorPanel.textContent = error.message;
    errorPanel.hidden = false;
  }
}

function labelWithInput(text, value, multiline = false) {
  const label = document.createElement("label");
  label.append(document.createTextNode(text));
  const input = document.createElement(multiline ? "textarea" : "input");
  input.value = value;
  input.required = true;
  input.maxLength = 500;
  label.append(input);
  return { label, input };
}

async function loadOrders() {
  const suffix = filter.value ? `?status=${encodeURIComponent(filter.value)}` : "";
  const orders = await api(`/api/orders${suffix}`);
  const container = document.querySelector("#orders");
  container.replaceChildren();
  document.querySelector("#empty").hidden = orders.length !== 0;
  for (const order of orders) {
    const card = document.createElement("article");
    card.dataset.orderId = order.id;
    const heading = document.createElement("h3");
    heading.textContent = order.title;
    const status = document.createElement("p");
    status.className = "order-status";
    status.textContent = order.status;
    const description = document.createElement("p");
    description.textContent = order.description;
    card.append(heading, status, description);
    if (order.status !== "Completed") {
      const advance = document.createElement("button");
      advance.type = "button";
      const next = order.status === "Pending" ? "In Progress" : "Completed";
      advance.textContent = next === "In Progress" ? "Start work" : "Complete work";
      advance.addEventListener("click", () => runAction(async () => {
        await api(`/api/orders/${order.id}/status`, "PATCH", { status: next });
        await loadOrders();
        feedback.textContent = `Order ${order.id} updated to ${next}.`;
      }));
      const edit = document.createElement("form");
      const titleField = labelWithInput("Edit title", order.title);
      const descriptionField = labelWithInput("Edit description", order.description, true);
      const save = document.createElement("button");
      save.type = "submit";
      save.textContent = "Save changes";
      edit.append(titleField.label, descriptionField.label, save);
      edit.addEventListener("submit", (event) => {
        event.preventDefault();
        runAction(async () => {
          await api(`/api/orders/${order.id}`, "PATCH", {
            title: titleField.input.value,
            description: descriptionField.input.value,
          });
          await loadOrders();
          feedback.textContent = `Order ${order.id} saved.`;
        });
      });
      card.append(advance, edit);
    }
    container.append(card);
  }
}

async function openWorkspace() {
  const customers = await api("/api/customers");
  const select = document.querySelector("#customers");
  select.replaceChildren();
  for (const customer of customers) {
    const option = document.createElement("option");
    option.value = customer.id;
    option.textContent = customer.name;
    select.append(option);
  }
  await loadOrders();
  loginPanel.hidden = true;
  workspace.hidden = false;
}

document.querySelector("#login-form").addEventListener("submit", (event) => {
  event.preventDefault();
  runAction(async () => {
    const fields = new FormData(event.target);
    await api("/api/login", "POST", {
      username: fields.get("username"),
      password: fields.get("password"),
    });
    event.target.reset();
    await openWorkspace();
  });
});

document.querySelector("#create-form").addEventListener("submit", (event) => {
  event.preventDefault();
  runAction(async () => {
    const fields = new FormData(event.target);
    const order = await api("/api/orders", "POST", {
      title: fields.get("title"),
      description: fields.get("description"),
      customer_id: Number(fields.get("customer_id")),
    });
    event.target.reset();
    filter.value = "";
    await loadOrders();
    feedback.textContent = `Order ${order.id} created.`;
  });
});

document.querySelector("#logout").addEventListener("click", () => runAction(async () => {
  await api("/api/logout", "POST");
  document.querySelector("#create-form").reset();
  filter.value = "";
  showLogin();
  feedback.textContent = "Signed out.";
}));

filter.addEventListener("change", () => runAction(loadOrders));

// An absent session is expected on first visit, not an application error.
(async () => {
  try {
    await openWorkspace();
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      showLogin();
    } else {
      errorPanel.textContent = error.message;
      errorPanel.hidden = false;
    }
  }
})();
