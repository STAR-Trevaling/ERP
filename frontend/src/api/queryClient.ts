import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 30, // 30 seconds
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export const API_BASE = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export interface CheckoutPayload {
  client_order_ref: string;
  customer: {
    name: string;
    phone: string;
    shipping_address: { street: string; city: string };
  };
  payment_method: string;
  hold_minutes: number;
  order_lines: Array<{
    sku: string;
    qty: number;
    price_unit: number;
  }>;
}

export interface AllocatePayload {
  sku: string;
  qty: number;
  order_ref: string;
  allow_split: boolean;
}

export interface WebhookPayload {
  gateway: 'vnpay' | 'momo';
  data: Record<string, any>;
}

// API Functions
export const api = {
  fetchStock: async (sku: string, mode: string = 'online', locationId?: number) => {
    const url = new URL(`${API_BASE}/inventory/stock/${sku}`);
    url.searchParams.append('mode', mode);
    if (locationId) url.searchParams.append('location_id', locationId.toString());

    const res = await fetch(url.toString());
    if (!res.ok) throw new Error(`Stock fetch error: ${res.statusText}`);
    return res.json();
  },

  checkout: async (payload: CheckoutPayload) => {
    const res = await fetch(`${API_BASE}/orders/checkout`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData?.detail?.message || 'Checkout failed');
    }
    return res.json();
  },

  allocateStock: async (payload: AllocatePayload) => {
    const res = await fetch(`${API_BASE}/inventory/allocate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error('Allocation computation failed');
    return res.json();
  },

  sendWebhook: async ({ gateway, data }: WebhookPayload) => {
    const endpoint = gateway === 'vnpay' ? 'webhooks/vnpay' : 'webhooks/momo';
    const res = await fetch(`${API_BASE}/${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return res.json();
  },
};
