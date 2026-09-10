// utils/api.js
//
// Thin fetch wrapper for BudgetNest's authenticated backend API.
//
// SECURITY NOTE (see FEATURE: USER-SPECIFIC DATA ISOLATION):
// Every request here attaches the signed-in user's JWT as a Bearer
// token. The backend (utils/deps.py -> get_current_user) resolves the
// acting user from that token alone and scopes every database query
// to it — this client never sends a user id of its own, and must
// never be changed to do so. Per-user isolation is enforced entirely
// server-side; this file's only job is to always send the right
// token and never silently fall back to unauthenticated/local data.

const API_BASE = (import.meta.env.VITE_API_URL || "http://localhost:8001/api").replace(/\/$/, "");

const TOKEN_KEY = "budgetnest_token";
const USER_KEY = "budgetnest_user";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

async function request(path, { method = "GET", body, params } = {}) {
  const token = getToken();
  if (!token) {
    throw new ApiError("Not authenticated", 401);
  }

  let url = `${API_BASE}${path}`;
  if (params) {
    const qs = new URLSearchParams(
      Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null)
        .map(([k, v]) => [k, String(v)])
    ).toString();
    if (qs) url += `?${qs}`;
  }

  let res;
  try {
    res = await fetch(url, {
      method,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (networkErr) {
    throw new ApiError("Unable to reach the server. Please check your connection.", 0);
  }

  if (res.status === 401) {
    // Token missing/expired/invalid. Never keep showing whatever was
    // last in memory — clear the session outright so the next person
    // to use this browser always lands on a fresh login, never a
    // leftover authenticated session belonging to someone else.
    clearSession();
    if (window.location.pathname !== "/login") {
      window.location.href = "/login";
    }
    throw new ApiError("Session expired. Please sign in again.", 401);
  }

  if (res.status === 204) {
    return null;
  }

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new ApiError(data.detail || data.message || "Request failed", res.status);
  }
  return data;
}

/**
 * Fetches every page of a paginated `{items, total}` list endpoint
 * and returns the combined items array.
 */
async function fetchAllPages(pageFetcher) {
  const pageSize = 100;
  let page = 1;
  let items = [];
  // Safety cap so a backend bug can never spin this into an infinite loop.
  for (let guard = 0; guard < 500; guard += 1) {
    const res = await pageFetcher(page, pageSize);
    items = items.concat(res.items || []);
    if (items.length >= (res.total ?? items.length) || (res.items || []).length === 0) {
      break;
    }
    page += 1;
  }
  return items;
}

export const api = {
  // --- Finance / starting balance ---------------------------------
  async getStartingBalance() {
    try {
      return await request("/finance/starting-balance");
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) return null;
      throw err;
    }
  },
  createStartingBalance(amount, date) {
    return request("/finance/starting-balance", { method: "POST", body: { amount, date } });
  },
  adjustStartingBalance(amount) {
    return request("/finance/starting-balance", { method: "PATCH", body: { amount } });
  },

  // --- Transactions -------------------------------------------------
  listAllTransactions() {
    return fetchAllPages((page, page_size) => request("/transactions", { params: { page, page_size } }));
  },
  createTransaction(payload) {
    return request("/transactions", { method: "POST", body: payload });
  },
  cancelTransaction(id) {
    return request(`/transactions/${id}`, { method: "DELETE" });
  },

  // --- Bills ----------------------------------------------------------
  async listAllBills() {
    const res = await request("/bills");
    return res.items || [];
  },
  createBill(payload) {
    return request("/bills", { method: "POST", body: payload });
  },
  payBill(id, paymentDate) {
    return request(`/bills/${id}/pay`, { method: "POST", body: { payment_date: paymentDate } });
  },
  cancelBill(id) {
    return request(`/bills/${id}`, { method: "DELETE" });
  },

  // --- Estimation (internally still the "money-given" API/collection —
  // see models/money_given.py for why the backend keeps that name) ------
  listAllEstimations() {
    return fetchAllPages((page, page_size) => request("/money-given", { params: { page, page_size } }));
  },
  createEstimation(payload) {
    return request("/money-given", { method: "POST", body: payload });
  },
  addRefund(id, payload) {
    return request(`/money-given/${id}/return`, { method: "POST", body: payload });
  },
  cancelEstimation(id) {
    return request(`/money-given/${id}`, { method: "DELETE" });
  },
  listRefunds(id) {
    return request(`/money-given/${id}/returns`);
  },
};
