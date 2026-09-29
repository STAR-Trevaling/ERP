import { create } from 'zustand';

export interface CartItem {
  id: string;
  sku: string;
  name: string;
  price: number;
  qty: number;
  color: string;
  size: string;
}

export interface CustomerInfo {
  name: string;
  phone: string;
  street: string;
}

interface CartState {
  selectedColor: string;
  selectedSize: string;
  cart: CartItem[];
  customer: CustomerInfo;
  paymentMethod: 'vnpay' | 'momo' | 'vietqr';
  
  setSelectedColor: (color: string) => void;
  setSelectedSize: (size: string) => void;
  setCustomer: (customer: Partial<CustomerInfo>) => void;
  setPaymentMethod: (method: 'vnpay' | 'momo' | 'vietqr') => void;
  getTotalAmount: () => number;
}

const computeSku = (color: string, size: string) => {
  const colorCode = color === 'Đen' ? 'DEN' : color === 'Trắng' ? 'TRANG' : 'NAVY';
  return `POLO-PIMA-${colorCode}-${size}`;
};

export const useCartStore = create<CartState>((set, get) => ({
  selectedColor: 'Đen',
  selectedSize: 'L',
  cart: [
    {
      id: 'polo-1',
      sku: 'POLO-PIMA-DEN-L',
      name: 'Áo Polo Nam Pima Cotton Cao Cấp',
      price: 450000,
      qty: 1,
      color: 'Đen',
      size: 'L'
    }
  ],
  customer: {
    name: 'Nguyễn Văn An',
    phone: '0988776655',
    street: '72 Lê Thánh Tôn, Bến Nghé, Quận 1, TP. Hồ Chí Minh'
  },
  paymentMethod: 'vnpay',

  setSelectedColor: (color) => {
    set((state) => {
      const newSku = computeSku(color, state.selectedSize);
      return {
        selectedColor: color,
        cart: state.cart.map(item => 
          item.id === 'polo-1' ? { ...item, color, sku: newSku } : item
        )
      };
    });
  },

  setSelectedSize: (size) => {
    set((state) => {
      const newSku = computeSku(state.selectedColor, size);
      return {
        selectedSize: size,
        cart: state.cart.map(item => 
          item.id === 'polo-1' ? { ...item, size, sku: newSku } : item
        )
      };
    });
  },

  setCustomer: (info) => {
    set((state) => ({ customer: { ...state.customer, ...info } }));
  },

  setPaymentMethod: (method) => {
    set({ paymentMethod: method });
  },

  getTotalAmount: () => {
    return get().cart.reduce((sum, item) => sum + item.price * item.qty, 0);
  }
}));
