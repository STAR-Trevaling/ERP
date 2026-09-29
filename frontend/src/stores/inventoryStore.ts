import { create } from 'zustand';

export interface LocationStock {
  id: number;
  name: string;
  code: string;
  type: 'central_dc' | 'retail_store' | 'transit';
  priority: number;
  buffer: number;
  onHand: number;
  reserved: number;
}

interface InventoryState {
  mode: 'online' | 'pos' | 'b2b' | 'audit';
  inspectSku: string;
  allocQty: number;
  allowSplit: boolean;
  locations: LocationStock[];

  setMode: (mode: 'online' | 'pos' | 'b2b' | 'audit') => void;
  setInspectSku: (sku: string) => void;
  setAllocQty: (qty: number) => void;
  setAllowSplit: (allow: boolean) => void;
  reserveStock: (locId: number, qty: number) => void;
  releaseStock: (locId: number, qty: number) => void;
}

export const useInventoryStore = create<InventoryState>((set) => ({
  mode: 'online',
  inspectSku: 'POLO-PIMA-DEN-L',
  allocQty: 10,
  allowSplit: false,
  locations: [
    {
      id: 1,
      name: 'Kho Tổng Phân Phối (Central DC)',
      code: 'WH/DC-01',
      type: 'central_dc',
      priority: 1,
      buffer: 0.0,
      onHand: 45,
      reserved: 0
    },
    {
      id: 2,
      name: 'Cửa hàng Bán lẻ Hà Nội (Store HN)',
      code: 'STORE/HN-01',
      type: 'retail_store',
      priority: 10,
      buffer: 2.0,
      onHand: 8,
      reserved: 0
    },
    {
      id: 3,
      name: 'Cửa hàng Bán lẻ TP.HCM (Store HCM)',
      code: 'STORE/HCM-01',
      type: 'retail_store',
      priority: 10,
      buffer: 2.0,
      onHand: 15,
      reserved: 0
    }
  ],

  setMode: (mode) => set({ mode }),
  setInspectSku: (inspectSku) => set({ inspectSku }),
  setAllocQty: (allocQty) => set({ allocQty }),
  setAllowSplit: (allowSplit) => set({ allowSplit }),

  reserveStock: (locId, qty) => {
    set((state) => ({
      locations: state.locations.map(loc => 
        loc.id === locId ? { ...loc, reserved: loc.reserved + qty } : loc
      )
    }));
  },

  releaseStock: (locId, qty) => {
    set((state) => ({
      locations: state.locations.map(loc => 
        loc.id === locId ? { ...loc, reserved: Math.max(0, loc.reserved - qty) } : loc
      )
    }));
  }
}));
