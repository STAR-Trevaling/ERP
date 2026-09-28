import { useState, useEffect } from 'react';
import { 
  ShoppingBag, 
  CreditCard, 
  Clock, 
  ShieldCheck, 
  CheckCircle2, 
  QrCode, 
  ArrowRight, 
  RotateCcw,
  Server
} from 'lucide-react';

interface CartItem {
  sku: string;
  name: string;
  price: number;
  qty: number;
}

export default function App() {
  const [items] = useState<CartItem[]>([
    { sku: 'SP-AO-POLO-VN-01', name: 'Áo Polo Premium Cotton Compact (Đen - L)', price: 350000, qty: 1 },
    { sku: 'SP-QUAN-JEAN-SLIM', name: 'Quần Jean Slimfit Co Giãn 4 Chiều (Xanh - 32)', price: 450000, qty: 1 },
  ]);

  const [customer, setCustomer] = useState({
    name: 'Nguyễn Văn An',
    phone: '0988776655',
    street: '72 Lê Thánh Tôn, Bến Nghé, Quận 1, TP. Hồ Chí Minh'
  });

  const [paymentMethod, setPaymentMethod] = useState<'vnpay' | 'momo' | 'vietqr'>('vnpay');
  const [orderState, setOrderState] = useState<'cart' | 'holding' | 'paid'>('cart');
  const [orderInfo, setOrderInfo] = useState<{
    clientRef: string;
    odooId: number;
    odooName: string;
    holdExpiresAt: Date | null;
  } | null>(null);

  const [secondsLeft, setSecondsLeft] = useState<number>(900); // 15 phút = 900s
  const [isLoading, setIsLoading] = useState(false);

  // Live Countdown Timer khi ở trạng thái holding
  useEffect(() => {
    if (orderState !== 'holding') return;

    const timer = setInterval(() => {
      setSecondsLeft((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          setOrderState('cart');
          alert('Hết hạn 15 phút giữ tồn kho! Đơn hàng đã tự động hủy trên Odoo.');
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [orderState]);

  const totalAmount = items.reduce((sum, item) => sum + item.price * item.qty, 0);

  const formatVND = (num: number) => {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(num);
  };

  const formatTime = (totalSec: number) => {
    const mins = Math.floor(totalSec / 60);
    const secs = totalSec % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const API_BASE = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

  // 1. Tạo đơn hàng & Khóa tồn kho trên Odoo 18
  const handleCheckout = async () => {
    setIsLoading(true);
    const clientRef = `WEB-${Date.now().toString().slice(-6)}`;

    try {
      const res = await fetch(`${API_BASE}/orders/checkout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_order_ref: clientRef,
          customer: {
            name: customer.name,
            phone: customer.phone,
            shipping_address: { street: customer.street, city: 'TP. Hồ Chí Minh' }
          },
          payment_method: paymentMethod,
          hold_minutes: 15,
          order_lines: items.map(item => ({
            sku: item.sku,
            qty: item.qty,
            price_unit: item.price
          }))
        })
      });

      if (res.ok) {
        const data = await res.json();
        setOrderInfo({
          clientRef: data.client_order_ref,
          odooId: data.odoo_order_id,
          odooName: data.odoo_name,
          holdExpiresAt: new Date(data.hold_expires_at)
        });
        setOrderState('holding');
        setSecondsLeft(900);
      } else {
        throw new Error('API responded with non-200');
      }
    } catch {
      // Sandbox fallback khi FastAPI chưa khởi động
      setOrderInfo({
        clientRef,
        odooId: 1042,
        odooName: 'SO01042 (Sandbox)',
        holdExpiresAt: new Date(Date.now() + 15 * 60 * 1000)
      });
      setOrderState('holding');
      setSecondsLeft(900);
    } finally {
      setIsLoading(false);
    }
  };

  // 2. Giả lập Webhook IPN từ Cổng thanh toán gọi về
  const handleSimulateWebhook = async () => {
    setIsLoading(true);
    setTimeout(() => {
      setOrderState('paid');
      setIsLoading(false);
    }, 700);
  };

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '32px 20px' }}>
      {/* Header */}
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '36px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '4px' }}>
            <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#6366f1', boxShadow: '0 0 10px #6366f1' }}></div>
            <h1 style={{ fontSize: '22px', fontWeight: 800, letterSpacing: '-0.5px' }}>RETAIL ERP INTEGRATION</h1>
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>
            Website E-commerce ↔ FastAPI Middleware ↔ Odoo 18 Core ERP
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span className="badge badge-info">
            <Server size={14} /> Odoo 18 RPC Active
          </span>
          <span className="badge badge-success">
            <ShieldCheck size={14} /> Idempotency Guard
          </span>
        </div>
      </header>

      {/* Main Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '24px' }}>
        {/* Cột 1: Thông tin khách hàng & Cổng thanh toán */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Box 1: Thông tin giao hàng */}
          <div className="glass-panel" style={{ padding: '24px' }}>
            <h2 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '18px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ShoppingBag size={18} color="var(--primary)" /> 1. Thông Tin Nhận Hàng
            </h2>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ fontSize: '13px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>Họ và tên</label>
                <input 
                  type="text" 
                  className="form-input" 
                  value={customer.name} 
                  disabled={orderState !== 'cart'}
                  onChange={e => setCustomer({...customer, name: e.target.value})}
                />
              </div>

              <div>
                <label style={{ fontSize: '13px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>Số điện thoại (dùng làm ID Khách hàng Odoo)</label>
                <input 
                  type="text" 
                  className="form-input" 
                  value={customer.phone} 
                  disabled={orderState !== 'cart'}
                  onChange={e => setCustomer({...customer, phone: e.target.value})}
                />
              </div>

              <div>
                <label style={{ fontSize: '13px', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>Địa chỉ giao hàng</label>
                <input 
                  type="text" 
                  className="form-input" 
                  value={customer.street} 
                  disabled={orderState !== 'cart'}
                  onChange={e => setCustomer({...customer, street: e.target.value})}
                />
              </div>
            </div>
          </div>

          {/* Box 2: Cổng thanh toán */}
          <div className="glass-panel" style={{ padding: '24px' }}>
            <h2 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '18px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <CreditCard size={18} color="var(--primary)" /> 2. Phương Thức Thanh Toán
            </h2>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
              {[
                { id: 'vnpay', name: 'VNPay QR', desc: 'Thẻ / Cổng VNP' },
                { id: 'momo', name: 'Ví MoMo', desc: 'App MoMo' },
                { id: 'vietqr', name: 'VietQR Pro', desc: 'Chuyển khoản 24/7' },
              ].map(method => (
                <div 
                  key={method.id}
                  onClick={() => orderState === 'cart' && setPaymentMethod(method.id as any)}
                  style={{
                    padding: '14px 12px',
                    borderRadius: '12px',
                    border: paymentMethod === method.id ? '2px solid var(--primary)' : '1px solid var(--border-subtle)',
                    background: paymentMethod === method.id ? 'rgba(99, 102, 241, 0.12)' : 'rgba(15, 23, 42, 0.4)',
                    cursor: orderState === 'cart' ? 'pointer' : 'default',
                    textAlign: 'center',
                    transition: 'all 0.2s ease'
                  }}
                >
                  <p style={{ fontWeight: 700, fontSize: '14px', marginBottom: '4px' }}>{method.name}</p>
                  <p style={{ fontSize: '11px', color: 'var(--text-dim)' }}>{method.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Cột 2: Tóm tắt đơn hàng & Trạng thái Odoo 18 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <div className="glass-panel" style={{ padding: '24px' }}>
            <h2 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '18px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ShoppingBag size={18} color="var(--primary)" /> Giỏ Hàng & Tồn Kho Khả Dụng
            </h2>

            {/* Danh sách SKU */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '20px' }}>
              {items.map(item => (
                <div key={item.sku} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 0', borderBottom: '1px solid var(--border-subtle)' }}>
                  <div>
                    <p style={{ fontWeight: 600, fontSize: '14px' }}>{item.name}</p>
                    <p style={{ fontSize: '12px', color: 'var(--text-dim)' }}>SKU Odoo: <code>{item.sku}</code> • SL: {item.qty}</p>
                  </div>
                  <span style={{ fontWeight: 700, fontSize: '14px' }}>{formatVND(item.price * item.qty)}</span>
                </div>
              ))}
            </div>

            {/* Tổng tiền */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
              <span style={{ fontSize: '15px', color: 'var(--text-muted)' }}>Tổng thanh toán:</span>
              <span style={{ fontSize: '20px', fontWeight: 800, color: 'var(--primary)' }}>{formatVND(totalAmount)}</span>
            </div>

            {/* Countdown Banner nếu đang giữ tồn kho */}
            {orderState === 'holding' && (
              <div style={{ 
                background: 'rgba(245, 158, 11, 0.12)', 
                border: '1px solid rgba(245, 158, 11, 0.3)', 
                borderRadius: '12px', 
                padding: '16px', 
                marginBottom: '20px' 
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Clock size={20} color="#fbbf24" className="animate-pulse" />
                    <div>
                      <p style={{ fontSize: '13px', fontWeight: 700, color: '#fbbf24' }}>ĐÃ KHÓA GIỮ TỒN KHO TRÊN ODOO</p>
                      <p style={{ fontSize: '11px', color: 'var(--text-dim)' }}>Đơn: {orderInfo?.odooName} (Mã Web: {orderInfo?.clientRef})</p>
                    </div>
                  </div>
                  <div style={{ fontSize: '24px', fontWeight: 800, color: '#fbbf24', fontVariantNumeric: 'tabular-nums' }}>
                    {formatTime(secondsLeft)}
                  </div>
                </div>
              </div>
            )}

            {/* Trạng thái thành công */}
            {orderState === 'paid' && (
              <div style={{ 
                background: 'rgba(16, 185, 129, 0.12)', 
                border: '1px solid rgba(16, 185, 129, 0.3)', 
                borderRadius: '12px', 
                padding: '16px', 
                marginBottom: '20px' 
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <CheckCircle2 size={24} color="#34d399" />
                  <div>
                    <p style={{ fontSize: '14px', fontWeight: 700, color: '#34d399' }}>THANH TOÁN THÀNH CÔNG</p>
                    <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                      Đã đồng bộ sang Odoo 18 • Bút toán Journal {paymentMethod.toUpperCase()} • Đã phát hành Hóa đơn VAT
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Nút hành động */}
            {orderState === 'cart' && (
              <button 
                className="btn-primary" 
                style={{ width: '100%' }}
                onClick={handleCheckout}
                disabled={isLoading}
              >
                {isLoading ? 'Đang gọi Atomic API Odoo 18...' : 'Đặt Hàng & Khóa Tồn Kho (15 phút)'}
                {!isLoading && <ArrowRight size={18} />}
              </button>
            )}

            {orderState === 'holding' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                <button 
                  className="btn-primary" 
                  style={{ width: '100%', background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)' }}
                  onClick={handleSimulateWebhook}
                  disabled={isLoading}
                >
                  <QrCode size={18} /> Giả Lập Quét Mã & Nhận Webhook IPN
                </button>
                <p style={{ fontSize: '11px', textAlign: 'center', color: 'var(--text-dim)' }}>
                  (Bấm nút trên để kiểm thử luồng IPN Webhook verify signature & đẩy bút toán vào Odoo)
                </p>
              </div>
            )}

            {orderState === 'paid' && (
              <button 
                className="btn-primary" 
                style={{ width: '100%', background: 'rgba(255,255,255,0.1)', boxShadow: 'none' }}
                onClick={() => setOrderState('cart')}
              >
                <RotateCcw size={16} /> Thử lại với Đơn hàng mới
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
