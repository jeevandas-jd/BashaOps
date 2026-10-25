// frontend/api.js
const API_BASE_URL = "http://localhost:8000";

export const api = {
  // 1. Submit a new message (Simulator)
  async submitMessage(messageData) {
    const response = await fetch(`${API_BASE_URL}/api/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(messageData),
    });
    return response.json();
  },

  // 2. Get all orders (for the dashboard inbox)
  async getOrders() {
    const response = await fetch(`${API_BASE_URL}/api/orders`);
    return response.json();
  },

  // 3. Resolve an ambiguous item in an order
  async resolveOrderItem(orderId, itemIndex, resolvedProductId) {
    const response = await fetch(
      `${API_BASE_URL}/api/orders/${orderId}/resolve?item_index=${itemIndex}&resolved_product_id=${resolvedProductId}`,
      { method: "POST" }
    );
    return response.json();
  },

  // 4. Confirm the order (triggers pricing & stock deduction)
  async confirmOrder(orderId) {
    const response = await fetch(`${API_BASE_URL}/api/orders/${orderId}/confirm`, {
      method: "POST",
    });
    return response.json();
  },

  // 5. Get the printable HTML bill (can be opened in a new tab or iframe)
  getBillUrl(orderId) {
    return `${API_BASE_URL}/api/orders/${orderId}/bill`;
  },
  
  // 6. Get catalogue products (for the resolution dropdown)
  async getProducts() {
    const response = await fetch(`${API_BASE_URL}/api/products`);
    return response.json();
  }
};