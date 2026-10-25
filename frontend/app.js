import { api } from "./api.js";

const escapeHTML = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (character) => {
    const entities = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    };
    return entities[character];
  });

function addChatBubble(text, type) {
  const history = document.getElementById("chat-history");
  const bubble = document.createElement("div");
  bubble.className = `chat-bubble ${type}`;
  bubble.textContent = text;
  history.appendChild(bubble);
  history.scrollTop = history.scrollHeight;
}

function renderAlerts(alerts) {
  const container = document.getElementById("alerts-container");
  container.innerHTML = alerts.length
    ? alerts
        .map(
          (alert) => `
            <div class="alert-card">
              <h3>⚠️ ${escapeHTML(alert.name)}</h3>
              <p>Current Stock: ${escapeHTML(alert.current_stock)}
                (Threshold: ${escapeHTML(alert.threshold)})</p>
            </div>
          `,
        )
        .join("")
    : "<p>No low-stock alerts.</p>";
}

function renderInventory(inventory) {
  const tbody = document.getElementById("inventory-body");
  if (!inventory.length) {
    tbody.innerHTML = '<tr><td colspan="5">No products found. Run scripts/seed_demo.py.</td></tr>';
    return;
  }

  tbody.innerHTML = inventory
    .map((item) => {
      const statusClass = item.is_low_stock ? "status-low" : "status-ok";
      const statusText = item.is_low_stock ? "LOW STOCK" : "Healthy";
      return `
        <tr>
          <td>${escapeHTML(item.name)}</td>
          <td>${escapeHTML(item.sku)}</td>
          <td>${escapeHTML(item.stock_quantity)}</td>
          <td>${escapeHTML(item.low_stock_threshold)}</td>
          <td class="${statusClass}">${statusText}</td>
        </tr>
      `;
    })
    .join("");
}

function renderLedger(ledger) {
  const tbody = document.getElementById("ledger-body");
  if (!ledger.length) {
    tbody.innerHTML = '<tr><td colspan="6">No stock movements yet.</td></tr>';
    return;
  }

  tbody.innerHTML = ledger
    .map((movement) => {
      const deltaClass = movement.quantity_delta < 0 ? "status-low" : "status-ok";
      const time = new Date(movement.created_at).toLocaleString();
      return `
        <tr>
          <td>${escapeHTML(time)}</td>
          <td>${escapeHTML(movement.product_id)}</td>
          <td>${escapeHTML(movement.movement_type)}</td>
          <td class="${deltaClass}">${escapeHTML(movement.quantity_delta)}</td>
          <td>${escapeHTML(movement.reference_id || "-")}</td>
          <td>${escapeHTML(movement.idempotency_key)}</td>
        </tr>
      `;
    })
    .join("");
}

function renderOrders(orders, products) {
  const container = document.getElementById("orders-container");
  if (!orders.length) {
    container.innerHTML = "<p>No orders yet. Send a message to get started.</p>";
    return;
  }

  container.innerHTML = orders
    .map((order) => {
      const items = order.items
        .map((item, index) => {
          const resolvedProduct = products.find(
            (product) => product.id === item.resolved_product_id,
          );
          const resolution = item.resolved_product_id
            ? `Matched: ${escapeHTML(resolvedProduct?.name || item.resolved_product_id)}`
            : `<label>
                Choose product:
                <select class="resolve-product" data-order-id="${escapeHTML(order.id)}"
                  data-item-index="${index}">
                  <option value="">Select a product</option>
                  ${products
                    .map(
                      (product) => `
                        <option value="${escapeHTML(product.id)}">
                          ${escapeHTML(product.name)} (${escapeHTML(product.sku)})
                        </option>
                      `,
                    )
                    .join("")}
                </select>
              </label>`;
          return `
            <li>
              ${escapeHTML(item.requested_quantity)} ${escapeHTML(item.requested_unit)}
              ${escapeHTML(item.product_mention)} — ${resolution}
            </li>
          `;
        })
        .join("");
      const status = escapeHTML(order.status);
      const actions =
        order.status === "READY_FOR_CONFIRMATION"
          ? `<button class="confirm-order" data-order-id="${escapeHTML(order.id)}">
               Confirm order
             </button>`
          : order.status === "CONFIRMED"
            ? `<a target="_blank" rel="noopener"
                 href="${escapeHTML(api.getBillUrl(order.id))}">View bill</a>`
            : "";

      return `
        <article class="order-card">
          <div class="order-heading">
            <strong>Order ${escapeHTML(order.id.slice(0, 8))}</strong>
            <span class="order-status">${status}</span>
          </div>
          <p>Received ${escapeHTML(new Date(order.created_at).toLocaleString())}</p>
          <ul>${items || "<li>No order items were extracted.</li>"}</ul>
          ${actions}
        </article>
      `;
    })
    .join("");
}

async function loadDashboard() {
  try {
    const [inventoryData, ledger, orderResponse, products] = await Promise.all([
      api.getInventory(),
      api.getLedger(),
      api.getOrders(),
      api.getProducts(),
    ]);
    if (!orderResponse.success) {
      throw new Error(orderResponse.message || "Could not load orders");
    }

    renderAlerts(inventoryData.low_stock_alerts || []);
    renderInventory(inventoryData.inventory || []);
    renderLedger(ledger || []);
    renderOrders(orderResponse.data?.orders || [], products || []);
    document.getElementById("connection-status").textContent = "Backend connected";
    document.getElementById("connection-status").className = "connected";
  } catch (error) {
    console.error("Failed to load dashboard:", error);
    document.getElementById("connection-status").textContent = error.message;
    document.getElementById("connection-status").className = "error";
    document.getElementById("inventory-body").innerHTML =
      '<tr><td colspan="5">Backend or database unavailable. Check the API server.</td></tr>';
    document.getElementById("ledger-body").innerHTML =
      '<tr><td colspan="6">Ledger unavailable.</td></tr>';
    document.getElementById("orders-container").textContent =
      "Orders unavailable. Check the API server.";
  }
}

async function sendMessage() {
  const input = document.getElementById("wa-input");
  const sendButton = document.getElementById("send-message");
  const message = input.value.trim();
  if (!message || sendButton.disabled) return;

  addChatBubble(message, "sent");
  sendButton.disabled = true;
  try {
    const conversationId =
      sessionStorage.getItem("bhashaops-conversation-id") || crypto.randomUUID();
    sessionStorage.setItem("bhashaops-conversation-id", conversationId);
    const response = await api.submitMessage({
      source: "simulator",
      external_message_id: crypto.randomUUID(),
      conversation_id: conversationId,
      sender_id: "simulator-user",
      text: message,
    });
    if (!response.success) {
      throw new Error(response.message || "Message processing failed");
    }
    input.value = "";
    addChatBubble("Message received and added to the order queue.", "received");
    await loadDashboard();
  } catch (error) {
    console.error("Failed to submit message:", error);
    addChatBubble(`Could not send message: ${error.message}`, "received");
  } finally {
    sendButton.disabled = false;
    input.focus();
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("send-message").addEventListener("click", sendMessage);
  document.getElementById("wa-input").addEventListener("keydown", (event) => {
    if (event.key === "Enter") sendMessage();
  });
  document.getElementById("orders-container").addEventListener("change", async (event) => {
    const select = event.target.closest(".resolve-product");
    if (!select || !select.value) return;
    select.disabled = true;
    try {
      await api.resolveOrderItem(
        select.dataset.orderId,
        Number(select.dataset.itemIndex),
        select.value,
      );
      await loadDashboard();
    } catch (error) {
      console.error("Failed to resolve order item:", error);
      document.getElementById("connection-status").textContent = error.message;
      document.getElementById("connection-status").className = "error";
      select.disabled = false;
    }
  });
  document.getElementById("orders-container").addEventListener("click", async (event) => {
    const button = event.target.closest(".confirm-order");
    if (!button) return;
    button.disabled = true;
    try {
      await api.confirmOrder(button.dataset.orderId);
      await loadDashboard();
    } catch (error) {
      console.error("Failed to confirm order:", error);
      document.getElementById("connection-status").textContent = error.message;
      document.getElementById("connection-status").className = "error";
      button.disabled = false;
    }
  });
  loadDashboard();
});
