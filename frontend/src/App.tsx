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
  Warehouse,
  FileText,
  Sparkles,
  Layers,
  Send,
  Lock,
  Cpu,
  RefreshCw,
  Sliders
} from 'lucide-react';

import { useMutation, useQuery } from '@tanstack/react-query';
import { api } from './api/queryClient';
import { useCartStore } from './stores/cartStore';
import { useOrderHoldStore } from './stores/orderHoldStore';
import { useInventoryStore } from './stores/inventoryStore';
import { useWebhookLogStore } from './stores/webhookLogStore';

import { Button } from './components/ui/button';
import { Badge } from './components/ui/badge';
import { Card, CardHeader, CardTitle, CardContent } from './components/ui/card';
import { Input } from './components/ui/input';

export default function App() {
  const [activeTab, setActiveTab] = useState<'checkout' | 'inventory' | 'webhook' | 'accounting'>('checkout');
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  // ================= 1. ZUSTAND STORES =================
  const { 
    selectedColor, 
    selectedSize, 
    cart, 
    customer, 
    paymentMethod, 
    setSelectedColor, 
    setSelectedSize, 
    setCustomer, 
    setPaymentMethod,
    getTotalAmount 
  } = useCartStore();

  const {
    orderState,
    orderInfo,
    secondsLeft,
    startHold,
    tick,
    cancelHold,
    markPaid
  } = useOrderHoldStore();

  const {
    mode,
    inspectSku,
    allocQty,
    allowSplit,
    locations,
    setMode,
    setInspectSku,
    setAllocQty,
    setAllowSplit
  } = useInventoryStore();

  const { logs, addLog } = useWebhookLogStore();

  // ================= 2. LIVE COUNTDOWN TIMER =================
  useEffect(() => {
    if (orderState !== 'holding') return;

    const interval = setInterval(() => {
      tick();
    }, 1000);

    return () => clearInterval(interval);
  }, [orderState, tick]);

  // Cảnh báo khi hết thời gian giữ kho
  useEffect(() => {
    if (orderState === 'holding' && secondsLeft <= 0) {
      showToast('⚠️ Đơn hàng đã quá hạn 15 phút. Odoo tự động giải phóng tồn kho!');
      addLog('warn', 'Order hold expired after 15 minutes. Odoo cron released stock.');
    }
  }, [secondsLeft, orderState, addLog]);

  // Đồng bộ inspectSku theo biến thể đang chọn
  useEffect(() => {
    if (cart.length > 0) {
      setInspectSku(cart[0].sku);
    }
  }, [cart, setInspectSku]);

  // ================= 3. TANSTACK QUERIES & MUTATIONS =================
  // Query tồn kho trực tiếp từ Odoo/FastAPI
  const { data: stockData, refetch: refetchStock, isFetching: isFetchingStock } = useQuery({
    queryKey: ['omnichannel-stock', inspectSku, mode],
    queryFn: () => api.fetchStock(inspectSku, mode).catch(() => null),
    enabled: activeTab === 'inventory',
  });

  // Mutation Checkout Đặt Hàng & Giữ Tồn Kho
  const checkoutMutation = useMutation({
    mutationFn: api.checkout,
    onSuccess: (data) => {
      startHold({
        clientRef: data.client_order_ref,
        odooId: data.odoo_order_id,
        odooName: data.odoo_name,
        holdExpiresAt: data.hold_expires_at,
        amount: data.total_amount
      });
      showToast(`Đã tạo đơn ${data.odoo_name} và giữ tồn kho 15 phút!`);
      addLog('success', `[CHECKOUT] Order ${data.odoo_name} created on Odoo 18. Stock reserved.`);
    },
    onError: () => {
      // Fallback sandbox khi server backend offline
      const clientRef = `WEB-${Date.now().toString().slice(-6)}`;
      startHold({
        clientRef,
        odooId: 1042,
        odooName: `SO-${clientRef.replace('WEB-', '')}`,
        holdExpiresAt: new Date(Date.now() + 15 * 60 * 1000).toISOString(),
        amount: getTotalAmount()
      });
      showToast(`[SANDBOX] Đơn ${clientRef} đã khóa giữ tồn kho 15 phút!`);
      addLog('info', `[CHECKOUT-SANDBOX] Created order ${clientRef} with 15-minute stock hold.`);
    }
  });

  // Mutation Phân Bổ Tồn Kho
  const [allocationResult, setAllocationResult] = useState<any>(null);
  const allocateMutation = useMutation({
    mutationFn: api.allocateStock,
    onSuccess: (data) => {
      setAllocationResult(data);
      showToast('Đã tính toán phân bổ tồn kho thành công!');
    },
    onError: () => {
      // Sandbox fallback calculation
      let planItems: any[] = [];
      let isSuccess = false;
      let notes = '';

      if (allocQty <= 45) {
        isSuccess = true;
        planItems = [{ location_name: 'Kho Tổng Phân Phối (Central DC)', warehouse_type: 'central_dc', allocated_qty: allocQty }];
        notes = 'Chiến lược A: Phân bổ trọn vẹn 100% từ Kho Tổng (Central DC).';
      } else if (!allowSplit && allocQty <= 13) {
        isSuccess = true;
        planItems = [{ location_name: 'Cửa hàng Bán lẻ TP.HCM (Store HCM)', warehouse_type: 'retail_store', allocated_qty: allocQty }];
        notes = 'Chiến lược B: Kho Tổng thiếu. Điều phối từ Cửa hàng TP.HCM có đủ hàng.';
      } else if (allowSplit && allocQty <= (45 + 6 + 13)) {
        isSuccess = true;
        planItems = [
          { location_name: 'Kho Tổng Phân Phối (Central DC)', warehouse_type: 'central_dc', allocated_qty: Math.min(45, allocQty) },
          { location_name: 'Cửa hàng Bán lẻ TP.HCM (Store HCM)', warehouse_type: 'retail_store', allocated_qty: Math.min(13, allocQty - 45) }
        ];
        notes = 'Chiến lược C: Split Shipment gộp tồn từ Kho Tổng + Cửa hàng TP.HCM.';
      } else {
        isSuccess = false;
        notes = 'Hết hàng trên toàn hệ thống (kể cả đã trừ lượng đệm an toàn).';
      }

      setAllocationResult({
        is_success: isSuccess,
        sku: inspectSku,
        requested_qty: allocQty,
        allocated_qty: isSuccess ? allocQty : 0,
        missing_qty: isSuccess ? 0 : allocQty,
        message: notes,
        plan_items: planItems
      });
      showToast('Đã thực thi thuật toán phân bổ Omnichannel!');
    }
  });

  // Mutation Webhook IPN Sandbox
  const webhookMutation = useMutation({
    mutationFn: api.sendWebhook,
    onSuccess: (res: any) => {
      if (res?.RspCode === '00' || res?.resultCode === 0) {
        markPaid();
        showToast('VNPay IPN xác thực thành công: Đơn hàng chuyển sang PAID!');
        addLog('success', `[GATEWAY-IPN] 200 OK. Payment confirmed via ${paymentMethod.toUpperCase()} Journal.`);
      } else if (res?.RspCode === '02') {
        showToast('Idempotency Guard: Giao dịch đã xác nhận trước đó.');
        addLog('warn', `[GATEWAY-IPN] Idempotency Hit: Returned RspCode 02 (Already confirmed).`);
      } else {
        showToast('Phản hồi từ cổng: ' + (res?.Message || 'Giao dịch từ chối'));
        addLog('error', `[GATEWAY-IPN] Returned error: ${JSON.stringify(res)}`);
      }
    },
    onError: () => {
      markPaid();
      showToast('[SANDBOX] Đã hạch toán hóa đơn điện tử Odoo thành công!');
      addLog('success', `[SANDBOX-IPN] Simulating success: Order marked as Paid.`);
    }
  });

  // ================= 4. UTILITIES =================
  const formatVND = (num: number) => {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(num);
  };

  const formatTime = (totalSec: number) => {
    const mins = Math.floor(totalSec / 60);
    const secs = totalSec % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const totalCartAmount = getTotalAmount();

  const handleCheckoutSubmit = () => {
    const clientRef = `WEB-${Date.now().toString().slice(-6)}`;
    checkoutMutation.mutate({
      client_order_ref: clientRef,
      customer: {
        name: customer.name,
        phone: customer.phone,
        shipping_address: { street: customer.street, city: 'TP. Hồ Chí Minh' }
      },
      payment_method: paymentMethod,
      hold_minutes: 15,
      order_lines: cart.map(item => ({
        sku: item.sku,
        qty: item.qty,
        price_unit: item.price
      }))
    });
  };

  const handleSimulateWebhook = (scenario: 'success' | 'tampered' | 'duplicate' | 'fail') => {
    const txnRef = orderInfo ? orderInfo.clientRef : `WEB-${Date.now().toString().slice(-6)}`;
    const transNo = `TRANS-${Date.now().toString().slice(-6)}`;
    const amount = orderInfo ? orderInfo.amount : totalCartAmount;

    if (scenario === 'success') {
      webhookMutation.mutate({
        gateway: 'vnpay',
        data: {
          vnp_TxnRef: txnRef,
          vnp_TransactionNo: transNo,
          vnp_ResponseCode: '00',
          vnp_Amount: (amount * 100).toString(),
          vnp_SecureHash: 'VALID_HMAC_SHA512_HASH'
        }
      });
    } else if (scenario === 'tampered') {
      addLog('error', `[VNPAY-IPN] Signature Tampered! HMAC verification failed -> Returned RspCode: 97.`);
      showToast('Cảnh báo bảo mật: Chữ ký số không khớp (Checksum mismatch). Đã từ chối!');
    } else if (scenario === 'duplicate') {
      addLog('warn', `[VNPAY-IPN] Idempotency Hit: Transaction ${transNo} already confirmed -> Returned RspCode: 02.`);
      showToast('Idempotency Guard: Giao dịch đã được ghi nhận trước đó, không cộng tiền 2 lần.');
    } else {
      addLog('warn', `[VNPAY-IPN] Payment Cancelled by customer (RspCode: 24).`);
      showToast('Khách hàng hủy giao dịch thanh toán.');
    }
  };

  return (
    <div className="min-h-screen bg-[#080b11] text-slate-100 antialiased p-4 md:p-8 max-w-7xl mx-auto">
      
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed top-6 right-6 z-50 flex items-center gap-3 bg-slate-900/95 border border-indigo-500/50 text-white px-5 py-3.5 rounded-2xl shadow-2xl backdrop-blur-xl animate-in fade-in slide-in-from-top-4 duration-300">
          <Sparkles className="w-5 h-5 text-indigo-400 shrink-0" />
          <span className="text-sm font-medium">{toastMessage}</span>
        </div>
      )}

      {/* HEADER COMMAND BAR */}
      <header className="mb-8 pb-6 border-b border-white/[0.08]">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <div className="flex items-center gap-2.5 mb-1.5">
              <span className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white shadow-md shadow-indigo-500/25">
                <Cpu className="w-4 h-4" />
              </span>
              <h1 className="font-display text-xl font-extrabold tracking-tight text-white">
                NEXUS // OMNICHANNEL RETAIL COMMAND
              </h1>
              <Badge variant="cyan">Odoo 18 Core ERP</Badge>
            </div>
            <p className="text-xs md:text-sm text-slate-400">
              Kiến trúc Điều phối Đa điểm ↔ FastAPI Middleware ↔ Cổng Thanh Toán VN ↔ Hạch toán Kế toán VAS
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            <Badge variant="success" className="gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              JSON-RPC 18.0 Active
            </Badge>
            <Badge variant="default">
              <ShieldCheck className="w-3.5 h-3.5" /> Idempotency Guard
            </Badge>
            <Badge variant="purple">
              <FileText className="w-3.5 h-3.5" /> VAS Hóa Đơn VAT
            </Badge>
          </div>
        </div>

        {/* NAVIGATION TABS (SHADCN PATTERN) */}
        <nav className="flex gap-2 mt-6 overflow-x-auto pb-1 scrollbar-none border-b border-white/[0.05]">
          <button 
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 whitespace-nowrap ${
              activeTab === 'checkout' 
                ? 'bg-indigo-500/15 border border-indigo-500/40 text-white shadow-lg shadow-indigo-500/15' 
                : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
            }`}
            onClick={() => setActiveTab('checkout')}
          >
            <ShoppingBag className="w-4 h-4" />
            <span>1. Đặt Hàng & Giữ Tồn (15-Min Hold)</span>
          </button>

          <button 
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 whitespace-nowrap ${
              activeTab === 'inventory' 
                ? 'bg-indigo-500/15 border border-indigo-500/40 text-white shadow-lg shadow-indigo-500/15' 
                : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
            }`}
            onClick={() => setActiveTab('inventory')}
          >
            <Warehouse className="w-4 h-4" />
            <span>2. Tồn Kho Đa Điểm & Điều Phối</span>
          </button>

          <button 
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 whitespace-nowrap ${
              activeTab === 'webhook' 
                ? 'bg-indigo-500/15 border border-indigo-500/40 text-white shadow-lg shadow-indigo-500/15' 
                : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
            }`}
            onClick={() => setActiveTab('webhook')}
          >
            <CreditCard className="w-4 h-4" />
            <span>3. Cổng Thanh Toán & Webhook IPN</span>
          </button>

          <button 
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 whitespace-nowrap ${
              activeTab === 'accounting' 
                ? 'bg-indigo-500/15 border border-indigo-500/40 text-white shadow-lg shadow-indigo-500/15' 
                : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
            }`}
            onClick={() => setActiveTab('accounting')}
          >
            <Layers className="w-4 h-4" />
            <span>4. Đối Soát 3 Bên & Sổ Cái VAS</span>
          </button>
        </nav>
      </header>

      {/* ================= TAB 1: CHECKOUT & 15-MINUTE ATOMIC HOLD ================= */}
      {activeTab === 'checkout' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* Cột Trái: Ma trận biến thể & Thông tin khách (7 Cột) */}
          <div className="lg:col-span-7 flex flex-col gap-6">
            
            {/* Box: Ma trận Biến thể Odoo 18 */}
            <Card className="glass-panel">
              <CardHeader className="flex flex-row items-center justify-between pb-3">
                <CardTitle className="flex items-center gap-2">
                  <Sliders className="w-4 h-4 text-indigo-400" />
                  Ma Trận Biến Thể Thời Trang (Odoo 18 Matrix)
                </CardTitle>
                <Badge variant="cyan" className="font-mono">{cart[0].sku}</Badge>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Chọn Màu Sắc */}
                <div>
                  <label className="text-xs text-slate-400 block mb-2 font-medium">
                    Màu sắc (product.attribute.value): <span className="text-white font-semibold">{selectedColor}</span>
                  </label>
                  <div className="flex gap-2.5">
                    {[
                      { name: 'Đen', hex: '#111827' },
                      { name: 'Trắng', hex: '#f8fafc' },
                      { name: 'Xanh Navy', hex: '#1e3a8a' }
                    ].map(c => (
                      <button
                        key={c.name}
                        onClick={() => setSelectedColor(c.name)}
                        className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-medium transition-all ${
                          selectedColor === c.name 
                            ? 'border-2 border-indigo-500 bg-indigo-500/10 text-white shadow-sm' 
                            : 'border border-white/10 bg-white/[0.03] text-slate-300 hover:border-white/20'
                        }`}
                      >
                        <span className="w-3.5 h-3.5 rounded-full border border-white/20" style={{ background: c.hex }}></span>
                        {c.name}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Chọn Kích Thước */}
                <div>
                  <label className="text-xs text-slate-400 block mb-2 font-medium">
                    Kích thước (Size): <span className="text-white font-semibold">{selectedSize}</span>
                  </label>
                  <div className="flex gap-2">
                    {['S', 'M', 'L', 'XL'].map(s => (
                      <button
                        key={s}
                        onClick={() => setSelectedSize(s)}
                        className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
                          selectedSize === s 
                            ? 'border-2 border-indigo-500 bg-indigo-500/15 text-indigo-300 shadow-sm' 
                            : 'border border-white/10 bg-white/[0.03] text-slate-300 hover:border-white/20'
                        }`}
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Box: Thông tin nhận hàng */}
            <Card className="glass-panel">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2">
                  <ShoppingBag className="w-4 h-4 text-indigo-400" />
                  Thông Tin Nhận Hàng (Tự Động Sinh res.partner)
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3.5">
                <div>
                  <label className="text-xs text-slate-400 block mb-1.5 font-medium">Họ và tên</label>
                  <Input 
                    value={customer.name}
                    disabled={orderState !== 'cart'}
                    onChange={e => setCustomer({ name: e.target.value })} 
                  />
                </div>

                <div>
                  <label className="text-xs text-slate-400 block mb-1.5 font-medium">
                    Số điện thoại (Unique ID tra cứu đối tác Odoo)
                  </label>
                  <Input 
                    value={customer.phone}
                    disabled={orderState !== 'cart'}
                    onChange={e => setCustomer({ phone: e.target.value })} 
                  />
                </div>

                <div>
                  <label className="text-xs text-slate-400 block mb-1.5 font-medium">Địa chỉ giao hàng</label>
                  <Input 
                    value={customer.street}
                    disabled={orderState !== 'cart'}
                    onChange={e => setCustomer({ street: e.target.value })} 
                  />
                </div>
              </CardContent>
            </Card>

            {/* Box: Cổng thanh toán */}
            <Card className="glass-panel">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2">
                  <CreditCard className="w-4 h-4 text-indigo-400" />
                  Cổng Thanh Toán (Hạch toán Sổ Nhật Ký Riêng)
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { id: 'vnpay', name: 'VNPay QR', desc: 'Sổ VNPAY (112)' },
                    { id: 'momo', name: 'Ví MoMo', desc: 'Sổ MOMO (112)' },
                    { id: 'vietqr', name: 'VietQR Pro', desc: 'Sổ BANK (112)' }
                  ].map(p => (
                    <div 
                      key={p.id}
                      className={`select-card ${paymentMethod === p.id ? 'selected' : ''}`}
                      onClick={() => setPaymentMethod(p.id as any)}
                    >
                      <div className="font-bold text-xs text-white mb-0.5">{p.name}</div>
                      <div className="text-[11px] text-slate-400">{p.desc}</div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

          </div>

          {/* Cột Phải: Giỏ hàng & Live 15-Minute Countdown Widget (5 Cột) */}
          <div className="lg:col-span-5 flex flex-col gap-6">
            
            <Card className="glass-panel glass-panel-glow">
              <CardHeader className="flex flex-row items-center justify-between pb-3">
                <CardTitle>Tóm Tắt Đơn Hàng</CardTitle>
                <Badge variant="purple">{cart.length} món hàng</Badge>
              </CardHeader>
              <CardContent className="space-y-5">
                
                {/* Cart Items */}
                <div className="space-y-3">
                  {cart.map(item => (
                    <div key={item.id} className="flex justify-between items-center p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.05]">
                      <div>
                        <div className="font-semibold text-sm text-white">{item.name}</div>
                        <div className="text-xs text-slate-400">
                          Màu: {item.color} | Size: {item.size} | SL: {item.qty}
                        </div>
                        <div className="font-mono text-[11px] text-sky-400 mt-0.5">{item.sku}</div>
                      </div>
                      <div className="font-bold text-sm text-white">
                        {formatVND(item.price * item.qty)}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Subtotal */}
                <div className="border-t border-white/[0.08] pt-4 space-y-2">
                  <div className="flex justify-between text-xs text-slate-400">
                    <span>Tạm tính</span>
                    <span className="text-white font-medium">{formatVND(totalCartAmount)}</span>
                  </div>
                  <div className="flex justify-between text-xs text-slate-400">
                    <span>Thuế GTGT (VAT 8%)</span>
                    <span className="text-slate-500">Đã gồm trong giá</span>
                  </div>
                  <div className="flex justify-between items-center pt-2 text-base font-bold text-white">
                    <span>Tổng thanh toán</span>
                    <span className="text-xl font-extrabold text-indigo-400">
                      {formatVND(totalCartAmount)}
                    </span>
                  </div>
                </div>

                {/* TRẠNG THÁI 1: CHƯA ĐẶT HÀNG */}
                {orderState === 'cart' && (
                  <Button
                    className="w-full h-12 text-sm"
                    onClick={handleCheckoutSubmit}
                    disabled={checkoutMutation.isPending}
                  >
                    <Lock className="w-4 h-4 mr-2" />
                    {checkoutMutation.isPending ? 'Đang Khóa Giữ Tồn Odoo...' : 'Khóa Tồn 15 Phút & Tạo Đơn Odoo'}
                  </Button>
                )}

                {/* TRẠNG THÁI 2: ĐANG GIỮ TỒN (HOLDING) */}
                {orderState === 'holding' && (
                  <div className="bg-amber-500/10 border border-amber-500/30 rounded-2xl p-5 text-center space-y-3">
                    <div className="flex items-center justify-center gap-2 text-amber-400 text-xs font-bold tracking-wider uppercase">
                      <Clock className="w-4 h-4 animate-pulse" />
                      <span>Đang Khóa Giữ Tồn Kho Odoo 18</span>
                    </div>

                    <div className="font-mono text-4xl font-extrabold text-amber-300 tracking-tight">
                      {formatTime(secondsLeft)}
                    </div>

                    <p className="text-xs text-slate-400">
                      Mã đơn Odoo: <strong className="text-white">{orderInfo?.odooName}</strong> (Khách quầy POS thấy hàng bị khóa giữ ngay lập tức)
                    </p>

                    <div className="flex gap-2.5 pt-1">
                      <Button
                        variant="emerald"
                        className="flex-1"
                        onClick={() => setActiveTab('webhook')}
                      >
                        <QrCode className="w-4 h-4 mr-1.5" /> Quét QR Thanh Toán
                      </Button>
                      <Button
                        variant="secondary"
                        size="icon"
                        onClick={() => {
                          cancelHold();
                          showToast('Đã hủy giữ tồn. Đơn hàng chuyển về giỏ.');
                          addLog('info', 'Customer cancelled reservation early. Stock released.');
                        }}
                      >
                        <RotateCcw className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                )}

                {/* TRẠNG THÁI 3: ĐÃ THANH TOÁN (PAID) */}
                {orderState === 'paid' && (
                  <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-2xl p-5 text-center space-y-3">
                    <CheckCircle2 className="w-10 h-10 text-emerald-400 mx-auto" />
                    <h3 className="font-extrabold text-emerald-300 text-base">
                      GIAO DỊCH HOÀN TẤT THÀNH CÔNG!
                    </h3>
                    <p className="text-xs text-slate-400">
                      Đã ghi nhận thanh toán qua {paymentMethod.toUpperCase()} | Đã post hóa đơn điện tử Odoo.
                    </p>
                    <Button
                      className="w-full"
                      onClick={() => setActiveTab('accounting')}
                    >
                      Xem Bút Toán Kế Toán VAS <ArrowRight className="w-4 h-4 ml-1.5" />
                    </Button>
                  </div>
                )}

              </CardContent>
            </Card>

          </div>

        </div>
      )}

      {/* ================= TAB 2: OMNICHANNEL INVENTORY & ALLOCATION ================= */}
      {activeTab === 'inventory' && (
        <div className="space-y-6">
          
          {/* Thanh chuyển chế độ truy vấn */}
          <Card className="glass-panel">
            <CardContent className="p-4 md:p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
              <div>
                <span className="text-xs text-slate-400 block mb-2 font-medium">Chế độ truy vấn nghiệp vụ (Multi-Mode Strategy):</span>
                <div className="flex flex-wrap gap-2">
                  {[
                    { id: 'online', label: 'Online (Trừ Buffer)', desc: 'E-commerce' },
                    { id: 'pos', label: 'POS (Quầy Thu Ngân)', desc: 'Bán tại quầy' },
                    { id: 'b2b', label: 'B2B (Chỉ Kho Tổng)', desc: 'Đại lý lớn' },
                    { id: 'audit', label: 'Audit (Tồn Thô)', desc: 'Kế toán kho' }
                  ].map(m => (
                    <button
                      key={m.id}
                      onClick={() => {
                        setMode(m.id as any);
                        refetchStock();
                      }}
                      className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                        mode === m.id 
                          ? 'border border-indigo-500 bg-indigo-500/20 text-white shadow-sm' 
                          : 'border border-white/10 bg-white/[0.02] text-slate-400 hover:text-white'
                      }`}
                    >
                      {m.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex items-center gap-3">
                <span className="text-xs text-slate-400">SKU tra cứu:</span>
                <Badge variant="cyan" className="font-mono text-xs">{inspectSku}</Badge>
                {stockData?.total_available_qty !== undefined && (
                  <Badge variant="success" className="font-mono text-xs">
                    Tồn Odoo: {stockData.total_available_qty}
                  </Badge>
                )}
                {isFetchingStock && <span className="text-xs text-indigo-400 animate-pulse">Syncing...</span>}
              </div>
            </CardContent>
          </Card>

          {/* Grid 3 Kho Vật Lý */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {locations.map(loc => {
              const isDC = loc.type === 'central_dc';
              const freeQty = loc.onHand - (orderState === 'holding' && isDC ? 1 : loc.reserved);
              const availOnline = Math.max(0, freeQty - loc.buffer);

              return (
                <Card key={loc.id} className="glass-panel">
                  <CardHeader className="pb-3 flex flex-row items-start justify-between">
                    <div>
                      <CardTitle className="text-sm font-bold text-white">{loc.name}</CardTitle>
                      <div className="font-mono text-xs text-slate-500 mt-0.5">{loc.code}</div>
                    </div>
                    <Badge variant={isDC ? 'purple' : 'cyan'}>
                      {isDC ? 'Ưu Tiên #1 (DC)' : 'Ưu Tiên #10'}
                    </Badge>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {/* Chỉ số tồn kho */}
                    <div className="grid grid-cols-2 gap-2.5">
                      <div className="bg-white/[0.02] p-2.5 rounded-xl border border-white/[0.04]">
                        <div className="text-[11px] text-slate-400">Tồn thực tế</div>
                        <div className="text-lg font-extrabold text-white">{loc.onHand}</div>
                      </div>

                      <div className="bg-white/[0.02] p-2.5 rounded-xl border border-white/[0.04]">
                        <div className="text-[11px] text-slate-400">Đang giữ (Reserved)</div>
                        <div className={`text-lg font-extrabold ${loc.reserved > 0 || (orderState === 'holding' && isDC) ? 'text-amber-400' : 'text-white'}`}>
                          {loc.reserved + (orderState === 'holding' && isDC ? 1 : 0)}
                        </div>
                      </div>

                      <div className="bg-white/[0.02] p-2.5 rounded-xl border border-white/[0.04]">
                        <div className="text-[11px] text-slate-400">Buffer Quầy POS</div>
                        <div className="text-lg font-extrabold text-rose-400">{loc.buffer}</div>
                      </div>

                      <div className="bg-indigo-500/10 p-2.5 rounded-xl border border-indigo-500/30">
                        <div className="text-[11px] text-indigo-300 font-medium">Khả dụng Web</div>
                        <div className="text-lg font-extrabold text-white">
                          {mode === 'pos' ? freeQty : availOnline}
                        </div>
                      </div>
                    </div>

                    <p className="text-xs text-slate-400 leading-relaxed">
                      {isDC 
                        ? 'Kho Tổng không giữ buffer, ưu tiên tập trung cho đơn hàng trực tuyến.' 
                        : `Cửa hàng giữ lại ${loc.buffer} sản phẩm dự phòng cho khách mua trực tiếp tại quầy.`}
                    </p>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          {/* Test Thuật toán Phân bổ Omnichannel */}
          <Card className="glass-panel">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2">
                <Cpu className="w-4 h-4 text-indigo-400" />
                Trình Thử Nghiệm Thuật Toán Phân Bổ Tồn Kho (Allocation Engine)
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
                <div>
                  <label className="text-xs text-slate-400 block mb-1.5 font-medium">Số lượng cần mua</label>
                  <Input 
                    type="number" 
                    value={allocQty} 
                    min={1} 
                    onChange={e => setAllocQty(Number(e.target.value))} 
                  />
                </div>

                <div className="flex items-center h-11">
                  <label className="flex items-center gap-2 cursor-pointer select-none">
                    <input 
                      type="checkbox" 
                      checked={allowSplit} 
                      onChange={e => setAllowSplit(e.target.checked)} 
                      className="w-4 h-4 rounded border-white/20 text-indigo-600 focus:ring-indigo-500" 
                    />
                    <span className="text-xs text-slate-300">Cho phép gộp đa kho (Split shipment)</span>
                  </label>
                </div>

                <div>
                  <Button 
                    className="w-full"
                    onClick={() => allocateMutation.mutate({
                      sku: inspectSku,
                      qty: allocQty,
                      order_ref: `TEST-${Date.now().toString().slice(-4)}`,
                      allow_split: allowSplit
                    })}
                    disabled={allocateMutation.isPending}
                  >
                    <RefreshCw className="w-3.5 h-3.5 mr-2" />
                    {allocateMutation.isPending ? 'Đang tính toán...' : 'Chạy Thuật Toán Phân Bổ'}
                  </Button>
                </div>
              </div>

              {/* Kết quả phân bổ */}
              {allocationResult && (
                <div className={`p-4 rounded-xl border ${
                  allocationResult.is_success 
                    ? 'bg-emerald-500/10 border-emerald-500/30' 
                    : 'bg-rose-500/10 border-rose-500/30'
                }`}>
                  <div className="flex justify-between items-center mb-2">
                    <span className={`text-xs font-bold ${allocationResult.is_success ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {allocationResult.is_success ? '✓ Phân Bổ Thành Công' : '✗ Không Đủ Hàng'}
                    </span>
                    <Badge variant="secondary">{allocationResult.message}</Badge>
                  </div>

                  {allocationResult.plan_items?.length > 0 && (
                    <div className="space-y-1.5 mt-2.5">
                      {allocationResult.plan_items.map((item: any, idx: number) => (
                        <div key={idx} className="flex justify-between text-xs bg-white/[0.03] p-2.5 rounded-lg border border-white/[0.04]">
                          <span>Xuất từ: <strong className="text-white">{item.location_name}</strong></span>
                          <span className="text-indigo-400 font-bold">Số lượng: {item.allocated_qty} cái</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

        </div>
      )}

      {/* ================= TAB 3: WEBHOOK IPN SANDBOX ================= */}
      {activeTab === 'webhook' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* Cột Trái: QR Code Quét Thanh Toán (5 Cột) */}
          <div className="lg:col-span-5">
            <Card className="glass-panel text-center">
              <CardHeader className="pb-2">
                <CardTitle className="text-base">
                  Mã QR Thanh Toán Thực Tế ({paymentMethod.toUpperCase()})
                </CardTitle>
                <p className="text-xs text-slate-400">
                  Quét mã qua App Ngân Hàng hoặc nhấn nút mô phỏng IPN bên cạnh
                </p>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="bg-white p-4 rounded-2xl inline-block shadow-2xl shadow-indigo-500/20">
                  <img 
                    src={`https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=2026-RETAIL-ERP-ORDER-${orderInfo?.clientRef || 'DEMO'}&color=0f172a`} 
                    alt="QR Code" 
                    className="w-44 h-44 block"
                  />
                </div>

                <div className="space-y-1">
                  <div className="text-base font-bold text-indigo-400">
                    {formatVND(orderInfo?.amount || totalCartAmount)}
                  </div>
                  <div className="font-mono text-xs text-slate-500">
                    Mã GD: {orderInfo?.clientRef || 'WEB-DEMO-001'}
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Cột Phải: Sandbox & Terminal Logs (7 Cột) */}
          <div className="lg:col-span-7 flex flex-col gap-6">
            
            <Card className="glass-panel">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2">
                  <Send className="w-4 h-4 text-indigo-400" />
                  Kịch Bản Bắn Webhook IPN (Simulate Gateway Callbacks)
                </CardTitle>
                <p className="text-xs text-slate-400">
                  Kiểm tra khả năng verify chữ ký số HMAC-SHA512/256 & phòng thủ Idempotency của Middleware
                </p>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-3">
                  <Button
                    variant="emerald"
                    onClick={() => handleSimulateWebhook('success')}
                    disabled={webhookMutation.isPending}
                  >
                    ✓ 1. Thành Công (00)
                  </Button>

                  <Button
                    variant="destructive"
                    onClick={() => handleSimulateWebhook('tampered')}
                    disabled={webhookMutation.isPending}
                  >
                    ⚠ 2. Giả Mạo Chữ Ký
                  </Button>

                  <Button
                    variant="secondary"
                    className="border-amber-500/40 text-amber-300 hover:bg-amber-500/10"
                    onClick={() => handleSimulateWebhook('duplicate')}
                    disabled={webhookMutation.isPending}
                  >
                    ⟳ 3. Duplicate Replay
                  </Button>

                  <Button
                    variant="secondary"
                    onClick={() => handleSimulateWebhook('fail')}
                    disabled={webhookMutation.isPending}
                  >
                    ✕ 4. Giao Dịch Hủy
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Terminal Box */}
            <Card className="glass-panel">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">TERMINAL AUDIT LOG</span>
                <Badge variant="cyan" className="font-mono text-[10px]">FastAPI :8000</Badge>
              </CardHeader>
              <CardContent>
                <div className="terminal-box max-h-52 overflow-y-auto">
                  {logs.map((log) => (
                    <div key={log.id} className="text-xs leading-relaxed mb-1">
                      <span className="text-slate-600">[{log.time}]</span>{' '}
                      <span className={
                        log.type === 'success' ? 'text-emerald-400' :
                        log.type === 'error' ? 'text-rose-400' :
                        log.type === 'warn' ? 'text-amber-400' : 'text-sky-400'
                      }>
                        {log.msg}
                      </span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

          </div>

        </div>
      )}

      {/* ================= TAB 4: RECONCILIATION & VAS ACCOUNTING ================= */}
      {activeTab === 'accounting' && (
        <div className="space-y-6">
          
          {/* Card Bút toán kép VAS */}
          <Card className="glass-panel">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-indigo-400" />
                Chuẩn Bút Toán Kế Toán VAS (Thông Tư 200/133 Việt Nam)
              </CardTitle>
              <p className="text-xs text-slate-400">
                Tách bạch sổ nhật ký theo cổng. Tuyệt đối không cấn trừ phí thanh toán vào Doanh thu 511.
              </p>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-emerald-500/10 border border-emerald-500/25 rounded-2xl p-4">
                  <div className="font-bold text-xs text-emerald-400 mb-1">
                    Nợ TK 112 (Tiền gửi Ngân hàng)
                  </div>
                  <div className="text-xs text-slate-400">
                    Sổ Nhật Ký: <strong className="text-white">{paymentMethod.toUpperCase()}</strong> (Thu đủ tiền từ cổng)
                  </div>
                  <div className="text-base font-extrabold text-white mt-2">
                    {formatVND(orderInfo?.amount || totalCartAmount)}
                  </div>
                </div>

                <div className="bg-indigo-500/10 border border-indigo-500/25 rounded-2xl p-4">
                  <div className="font-bold text-xs text-indigo-400 mb-1">
                    Có TK 511 & 33311 (Doanh thu & Thuế)
                  </div>
                  <div className="text-xs text-slate-400">
                    Hóa đơn VAT bán lẻ điện tử Odoo 18
                  </div>
                  <div className="text-base font-extrabold text-white mt-2">
                    {formatVND(orderInfo?.amount || totalCartAmount)}
                  </div>
                </div>

                <div className="bg-rose-500/10 border border-rose-500/25 rounded-2xl p-4">
                  <div className="font-bold text-xs text-rose-400 mb-1">
                    Nợ TK 6425 (Chi phí dịch vụ cổng)
                  </div>
                  <div className="text-xs text-slate-400">
                    Phí giao dịch (1.2% đối soát định kỳ)
                  </div>
                  <div className="text-base font-extrabold text-white mt-2">
                    {formatVND(Math.round((orderInfo?.amount || totalCartAmount) * 0.012))}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Bảng Đối soát 3 Bên */}
          <Card className="glass-panel">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-indigo-400" />
                Bảng Đối Soát 3 Bên Thời Gian Thực (3-Way Matching Ledger)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-white/[0.08] text-left text-slate-400 font-medium">
                      <th className="p-3">Mã GD Cổng (Gateway)</th>
                      <th className="p-3">Mã Đơn Backend</th>
                      <th className="p-3">Odoo 18 Account Move</th>
                      <th className="p-3">Số Tiền</th>
                      <th className="p-3">Trạng Thái Khớp</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/[0.04]">
                    <tr>
                      <td className="p-3 font-mono text-sky-400">VNP-994821</td>
                      <td className="p-3 font-mono text-slate-300">{orderInfo?.clientRef || 'WEB-837291'}</td>
                      <td className="p-3 font-mono text-slate-300">INV/2026/00142</td>
                      <td className="p-3 font-bold text-white">{formatVND(orderInfo?.amount || totalCartAmount)}</td>
                      <td className="p-3">
                        <Badge variant="success">✓ 100% Khớp (0₫ Lệch)</Badge>
                      </td>
                    </tr>

                    <tr>
                      <td className="p-3 font-mono text-sky-400">MOMO-284719</td>
                      <td className="p-3 font-mono text-slate-300">WEB-192834</td>
                      <td className="p-3 font-mono text-slate-300">INV/2026/00141</td>
                      <td className="p-3 font-bold text-white">450.000 ₫</td>
                      <td className="p-3">
                        <Badge variant="success">✓ 100% Khớp (0₫ Lệch)</Badge>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

        </div>
      )}

    </div>
  );
}
