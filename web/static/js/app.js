/**
 * Flight Finder AI Agent - Frontend JavaScript
 * Includes: search, airlines management, AI chat, mailto email
 */

const API_BASE = '';
let lastSearchResults = null;

// ============ EMAIL CHECKBOX TOGGLE ============

document.getElementById('sendEmail').addEventListener('change', (e) => {
    const show = e.target.checked;
    document.getElementById('emailGroup').style.display = show ? 'block' : 'none';
    document.getElementById('maxResultsGroup').style.display = show ? 'block' : 'none';
});

// ============ AIRLINES MANAGEMENT ============

async function loadAirlines() {
    try {
        const resp = await fetch(`${API_BASE}/api/airlines`);
        const data = await resp.json();
        renderAirlines(data);
    } catch (e) {
        document.getElementById('airlinesList').innerHTML = '<span class="error-message">Chyba nacitania</span>';
    }
}

function renderAirlines(data) {
    const container = document.getElementById('airlinesList');
    const active = data.active_airlines || [];
    const available = data.available_airlines || [];

    let html = '';
    available.forEach(code => {
        const isActive = active.includes(code);
        const label = code.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
        html += `
            <span class="airline-tag ${isActive ? 'active' : 'inactive'}">
                ${isActive ? '>' : ' '} ${label}
                <button onclick="toggleAirline('${code}', ${isActive})" title="${isActive ? 'Odstranit' : 'Pridat'}">
                    ${isActive ? 'x' : '+'}
                </button>
            </span>
        `;
    });
    container.innerHTML = html;
}

async function toggleAirline(code, isActive) {
    const endpoint = isActive ? '/api/airlines/remove' : '/api/airlines/add';
    try {
        await fetch(`${API_BASE}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ airline_code: code })
        });
        loadAirlines();
    } catch (e) {
        alert('Chyba: ' + e.message);
    }
}

// ============ FLIGHT SEARCH ============

document.getElementById('searchForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const btn = e.target.querySelector('.btn-search');
    btn.disabled = true;
    btn.textContent = 'Hladam...';

    const payload = {
        origin: document.getElementById('origin').value.toUpperCase(),
        destination: document.getElementById('destination').value.toUpperCase(),
        departure_date: document.getElementById('departure_date').value,
        return_date: document.getElementById('return_date').value,
        adults: parseInt(document.getElementById('adults').value),
    };

    try {
        const resp = await fetch(`${API_BASE}/api/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await resp.json();

        if (data.error) {
            showError(data.error);
        } else {
            lastSearchResults = data;
            renderResults(data);
            // Show email button if checkbox is checked
            if (document.getElementById('sendEmail').checked) {
                document.getElementById('emailBtn').style.display = 'block';
            }
        }
    } catch (e) {
        showError('Chyba pripojenia k serveru: ' + e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Hladat lety';
    }
});

function renderResults(data) {
    const section = document.getElementById('resultsSection');
    const content = document.getElementById('resultsContent');
    section.style.display = 'block';

    let html = '';

    if (data.errors && data.errors.length > 0) {
        data.errors.forEach(err => {
            if (err) html += `<div class="error-message">! ${err}</div>`;
        });
    }

    if (data.outbound_flights && data.outbound_flights.length > 0) {
        html += '<h3 style="margin: 16px 0 8px; color: #fff;">Odletove lety</h3>';
        html += buildFlightTable(data.outbound_flights);
    } else {
        html += '<div class="no-results">Ziadne odletove lety neboli najdene.</div>';
    }

    if (data.return_flights && data.return_flights.length > 0) {
        html += '<h3 style="margin: 24px 0 8px; color: #fff;">Spiatocne lety</h3>';
        html += buildFlightTable(data.return_flights);
    }

    content.innerHTML = html;
    section.scrollIntoView({ behavior: 'smooth' });
}

function buildFlightTable(flights) {
    let html = `
        <table class="results-table">
            <thead>
                <tr>
                    <th>Spolocnost</th>
                    <th>Let</th>
                    <th>Trasa</th>
                    <th>Odlet</th>
                    <th>Cena</th>
                    <th>Booking</th>
                </tr>
            </thead>
            <tbody>
    `;

    flights.forEach((flight, i) => {
        const depTime = formatDateTime(flight.departure_time);
        const rowClass = i === 0 ? 'cheapest-row' : '';

        html += `
            <tr class="${rowClass}">
                <td>${flight.airline}</td>
                <td>${flight.flight_number || '-'}</td>
                <td>${flight.origin} > ${flight.destination}</td>
                <td>${depTime}</td>
                <td class="price-cell">${flight.price} ${flight.currency}${i === 0 ? ' *' : ''}</td>
                <td><a href="${flight.booking_url}" target="_blank" class="booking-link">Kupit</a></td>
            </tr>
        `;
    });

    html += '</tbody></table>';
    return html;
}

function formatDateTime(isoString) {
    if (!isoString) return '-';
    try {
        const d = new Date(isoString);
        return d.toLocaleDateString('sk-SK', { day: '2-digit', month: '2-digit' }) + ' ' +
               d.toLocaleTimeString('sk-SK', { hour: '2-digit', minute: '2-digit' });
    } catch {
        return isoString;
    }
}

function showError(message) {
    const section = document.getElementById('resultsSection');
    const content = document.getElementById('resultsContent');
    section.style.display = 'block';
    content.innerHTML = `<div class="error-message">Chyba: ${message}</div>`;
}

// ============ EMAIL (MAILTO) ============

function sendEmailWithResults() {
    if (!lastSearchResults) return;

    const email = document.getElementById('emailAddress').value;
    if (!email) {
        alert('Zadaj emailovu adresu!');
        return;
    }

    const maxResults = parseInt(document.getElementById('maxEmailResults').value) || 3;
    const search = lastSearchResults.search || {};
    const flights = (lastSearchResults.outbound_flights || []).slice(0, maxResults);

    if (flights.length === 0) {
        alert('Ziadne vysledky na odoslanie.');
        return;
    }

    // Build email subject
    const cheapest = flights[0];
    const subject = `Letenky ${search.origin}>${search.destination} | od ${cheapest.price} ${cheapest.currency} | ${search.departure_date}`;

    // Build email body
    let body = `Najlacnejsie lety (${search.origin} > ${search.destination}, ${search.departure_date}):\n\n`;

    flights.forEach((flight, i) => {
        const depDate = flight.departure_time ? new Date(flight.departure_time).toLocaleString('sk-SK') : '';
        body += `${i + 1}. ${flight.airline} | ${flight.origin} > ${flight.destination}\n`;
        body += `   Odlet: ${depDate}\n`;
        body += `   Cena: ${flight.price} ${flight.currency}\n`;
        body += `   Booking: ${flight.booking_url}\n\n`;
    });

    body += `---\nVygenerovane: ${new Date().toLocaleString('sk-SK')}\n`;
    body += `Flight Finder AI Agent`;

    // Create mailto link and open
    const mailtoLink = `mailto:${encodeURIComponent(email)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    window.location.href = mailtoLink;
}

// ============ AI CHAT ============

document.getElementById('chatForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    if (!message) return;

    addChatMessage('user', message);
    input.value = '';
    addChatMessage('assistant', 'Premyslam...');

    try {
        const resp = await fetch(`${API_BASE}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });

        const data = await resp.json();
        const messages = document.getElementById('chatMessages');
        messages.removeChild(messages.lastChild);

        if (data.error) {
            addChatMessage('assistant', 'Chyba: ' + data.error);
        } else {
            addChatMessage('assistant', data.response);
        }
    } catch (e) {
        const messages = document.getElementById('chatMessages');
        messages.removeChild(messages.lastChild);
        addChatMessage('assistant', 'Chyba pripojenia: ' + e.message);
    }
});

function addChatMessage(role, text) {
    const container = document.getElementById('chatMessages');
    const div = document.createElement('div');
    div.className = `chat-message ${role}`;
    div.textContent = text;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

// ============ INIT ============

document.addEventListener('DOMContentLoaded', () => {
    loadAirlines();
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('departure_date').min = today;
    document.getElementById('return_date').min = today;
});