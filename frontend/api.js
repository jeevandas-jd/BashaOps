const API_BASE =
  window.BASHAOPS_API_BASE || "http://localhost:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, options);
  const contentType = response.headers.get("content-type") || "";
  const body = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const detail =
      typeof body === "object" && body !== null
        ? body.detail || body.message
        : body;
    throw new Error(detail || `Request failed with status ${response.status}`);
  }
  return body;
}

export const api = {
  submitMessage(messageData) {
    return request("/api/messages", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(messageData),
    });
  },

  getOrders() {
    return request("/api/orders");
  },

  resolveOrderItem(orderId, itemIndex, resolvedProductId) {
    const query = new URLSearchParams({
      item_index: String(itemIndex),
      resolved_product_id: resolvedProductId,
    });
    return request(`/api/orders/${encodeURIComponent(orderId)}/resolve?${query}`, {
      method: "POST",
    });
  },

  confirmOrder(orderId) {
    return request(`/api/orders/${encodeURIComponent(orderId)}/confirm`, {
      method: "POST",
    });
  },

  getBillUrl(orderId) {
    return `${API_BASE}/api/orders/${encodeURIComponent(orderId)}/bill`;
  },

  getProducts() {
    return request("/api/products");
  },

  getInventory() {
    return request("/api/inventory");
  },

  getLedger() {
    return request("/api/inventory/ledger");
  },
};
