// frontend/app.js
// IMPORTANT: Change this if your backend runs on a different port
const API_BASE = 'http://localhost:8000'; 

async function loadDashboard() {
    try {
        const [inventoryRes, ledgerRes] = await Promise.all([
            fetch(`${API_BASE}/api/inventory`),
            fetch(`${API_BASE}/api/inventory/ledger`)
        ]);

        const inventoryData = await inventoryRes.json();
        const ledgerData = await ledgerRes.json();

        renderAlerts(inventoryData.low_stock_alerts);
        renderInventory(inventoryData.inventory);
        renderLedger(ledgerData);
    } catch (error) {
        console.error("Failed to load dashboard:", error);
        alert("Error connecting to backend. Is FastAPI running on port 8000?");
    }
}

function renderAlerts(alerts) {
    const section = document.getElementById('alerts-section');
    const container = document.getElementById('alerts-container');
    
    if (alerts && alerts.length > 0) {
        section.classList.remove('hidden');
        container.innerHTML = alerts.map(alert => `
            <div class="alert-card">
                <h3>⚠️ ${alert.name}</h3>
                <p>Current Stock: ${alert.current_stock} (Threshold: ${alert.threshold})</p>
            </div>
        `).join('');
    } else {
        section.classList.add('hidden');
    }
}

function renderInventory(inventory) {
    const tbody = document.getElementById('inventory-body');
    if (!inventory || inventory.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6">No products found. Run seed_demo.py!</td></tr>';
        return;
    }

    tbody.innerHTML = inventory.map(item => {
        const isLow = item.is_low_stock;
        const statusClass = isLow ? 'status-low' : 'status-ok';
        const statusText = isLow ? 'LOW STOCK' : 'Healthy';
        
        // Note: We don't have price in the /api/inventory endpoint, 
        // so we just show stock data here.
        return `
            <tr>
                <td>${item.name}</td>
                <td>${item.sku}</td>
                <td>-</td> 
                <td>${item.stock_quantity}</td>
                <td>${item.low_stock_threshold}</td>
                <td class="${statusClass}">${statusText}</td>
            </tr>
        `;
    }).join('');
}

function renderLedger(ledger) {
    const tbody = document.getElementById('ledger-body');
    if (!ledger || ledger.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6">No stock movements yet. Confirm an order to see data here!</td></tr>';
        return;
    }

    tbody.innerHTML = ledger.map(m => {
        const deltaClass = m.quantity_delta < 0 ? 'status-low' : 'status-ok';
        const time = new Date(m.created_at).toLocaleString();
        
        return `
            <tr>
                <td>${time}</td>
                <td>${m.product_id}</td>
                <td>${m.movement_type}</td>
                <td class="${deltaClass}">${m.quantity_delta}</td>
                <td>${m.reference_id || '-'}</td>
                <td><span class="ledger-key">${m.idempotency_key}</span></td>
            </tr>
        `;
    }).join('');
}

// Initial load
document.addEventListener('DOMContentLoaded', loadDashboard);