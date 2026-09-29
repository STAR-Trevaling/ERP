import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface OrderInfo {
  clientRef: string;
  odooId: number;
  odooName: string;
  holdExpiresAt: string;
  amount: number;
}

interface OrderHoldState {
  orderState: 'cart' | 'holding' | 'paid';
  orderInfo: OrderInfo | null;
  secondsLeft: number;

  startHold: (info: OrderInfo) => void;
  tick: () => void;
  cancelHold: () => void;
  markPaid: () => void;
  reset: () => void;
}

export const useOrderHoldStore = create<OrderHoldState>()(
  persist(
    (set, get) => ({
      orderState: 'cart',
      orderInfo: null,
      secondsLeft: 900,

      startHold: (info) => {
        set({
          orderState: 'holding',
          orderInfo: info,
          secondsLeft: 900
        });
      },

      tick: () => {
        const current = get().secondsLeft;
        if (current <= 1) {
          set({
            orderState: 'cart',
            secondsLeft: 0,
            orderInfo: null
          });
        } else {
          set({ secondsLeft: current - 1 });
        }
      },

      cancelHold: () => {
        set({
          orderState: 'cart',
          orderInfo: null,
          secondsLeft: 900
        });
      },

      markPaid: () => {
        set({
          orderState: 'paid'
        });
      },

      reset: () => {
        set({
          orderState: 'cart',
          orderInfo: null,
          secondsLeft: 900
        });
      }
    }),
    {
      name: 'nexus-order-hold-storage'
    }
  )
);
