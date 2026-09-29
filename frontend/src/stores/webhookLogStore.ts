import { create } from 'zustand';

export interface LogItem {
  id: string;
  time: string;
  type: 'info' | 'success' | 'warn' | 'error';
  msg: string;
}

interface WebhookLogState {
  logs: LogItem[];
  addLog: (type: 'info' | 'success' | 'warn' | 'error', msg: string) => void;
  clearLogs: () => void;
}

export const useWebhookLogStore = create<WebhookLogState>((set) => ({
  logs: [
    {
      id: 'init',
      time: '18:00:00',
      type: 'info',
      msg: 'Nexus Gateway & Idempotency listener initialized.'
    }
  ],

  addLog: (type, msg) => {
    const time = new Date().toLocaleTimeString('vi-VN');
    const newLog: LogItem = {
      id: `${Date.now()}-${Math.random()}`,
      time,
      type,
      msg
    };
    set((state) => ({
      logs: [newLog, ...state.logs.slice(0, 24)]
    }));
  },

  clearLogs: () => set({ logs: [] })
}));
