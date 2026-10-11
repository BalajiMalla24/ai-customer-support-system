import { useMemo, useRef, useState } from "react";
import ChatWindow from "./ChatWindow";

const PRODUCTS = [
  {
    id: "p1",
    name: "Bluetooth Speaker",
    price: 2499,
    model: "JBL Go 3",
    stock: "In Stock",
    image:
      "https://images.unsplash.com/photo-1589003077984-894e133dabab?auto=format&fit=crop&w=900&q=80",
  },
  {
    id: "p2",
    name: "Wireless Earphones",
    price: 1299,
    model: "boAt Airdopes",
    stock: "In Stock",
    image:
      "https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?auto=format&fit=crop&w=900&q=80",
  },
  {
    id: "p3",
    name: "USB-C Fast Charger",
    price: 599,
    model: "Anker 20W",
    stock: "In Stock",
    image:
      "https://images.unsplash.com/photo-1583863788434-e58a36330cf0?auto=format&fit=crop&w=900&q=80",
  },
  {
    id: "p4",
    name: "Laptop Stand",
    price: 1899,
    model: "AmazonBasics",
    stock: "In Stock",
    image:
      "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?auto=format&fit=crop&w=900&q=80",
  },
];

const formatInr = (amount) => `Rs. ${amount.toLocaleString("en-IN")}`;

const getOrCreateSessionId = () => {
  let sid = localStorage.getItem("chat_session_id");
  if (!sid) {
    sid = Math.random().toString(36).slice(2, 10);
    localStorage.setItem("chat_session_id", sid);
  }
  return sid;
};

const generateOrderId = () => `SE-${Math.floor(1000 + Math.random() * 9000)}`;
const sessionFromOrder = (orderId) =>
  `order-${String(orderId || "general").toUpperCase()}`;

const ShopEasy = ({ onOpenOrderSupport }) => {
  const [cart, setCart] = useState([]);
  const [orders, setOrders] = useState([]);
  const [latestOrder, setLatestOrder] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [cartOpen, setCartOpen] = useState(false);
  const autoSentOrderIdsRef = useRef(new Set());

  const cartCount = useMemo(() => cart.length, [cart]);
  const cartTotal = useMemo(
    () => cart.reduce((sum, item) => sum + item.price, 0),
    [cart],
  );

  const addToCart = (product) => {
    setCart((prev) => [...prev, product]);
  };

  const removeFromCart = (index) => {
    setCart((prev) => prev.filter((_, i) => i !== index));
  };

  const sendOrderContextToWs = (order) => {
    if (!order?.order_id) return;
    if (autoSentOrderIdsRef.current.has(order.order_id)) return;

    const sessionId =
      sessionFromOrder(order.order_id) || getOrCreateSessionId();
    const socket = new WebSocket(`ws://localhost:8000/ws/chat/${sessionId}`);

    socket.onopen = () => {
      const combinedMsg = `Customer just placed order ${order.order_id} for ${order.product_name} at Rs. ${order.price}. Hi! I just placed order ${order.order_id}. Can you confirm it?`;
      socket.send(
        JSON.stringify({
          type: "chat_message",
          text: combinedMsg,
          order_id: order.order_id,
        }),
      );
      autoSentOrderIdsRef.current.add(order.order_id);
      setTimeout(() => socket.close(), 500);
    };

    socket.onerror = () => {
      socket.close();
    };
  };

  const buyNow = async (product) => {
    const order = {
      order_id: generateOrderId(),
      product_name: product.name,
      price: product.price,
      status: "In Transit",
      customer: "Arjun",
      customer_name: "Arjun",
    };

    setOrders((prev) => [order, ...prev]);
    setLatestOrder(order);
    setShowModal(true);

    try {
      await fetch("http://localhost:8000/api/mock/order", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          order_id: order.order_id,
          product_name: order.product_name,
          price: order.price,
          customer_name: order.customer_name,
        }),
      });
    } catch (err) {
      console.error("Order API error:", err);
    }

    setTimeout(() => {
      setChatOpen(true);
      sendOrderContextToWs(order);
    }, 2000);

    if (typeof onOpenOrderSupport === "function") {
      onOpenOrderSupport(order.order_id, "orders");
    }
  };

  const checkoutCart = async () => {
    if (cart.length === 0) return;
    const firstItem = cart[0];
    setCartOpen(false);
    await buyNow(firstItem);
    setCart([]);
  };

  return (
    <div className="w-full min-h-screen bg-white text-zinc-900">
      <nav className="w-full border-b border-zinc-200 bg-white sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 md:px-6 h-16 flex items-center justify-between">
          <h1 className="text-xl font-semibold tracking-tight">ShopEasy</h1>
          <div className="relative">
            <button
              onClick={() => setCartOpen((v) => !v)}
              className="w-10 h-10 rounded-full border border-zinc-300 flex items-center justify-center hover:bg-zinc-50 transition-colors"
            >
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <circle cx="9" cy="21" r="1" />
                <circle cx="20" cy="21" r="1" />
                <path d="M1 1h4l2.68 13.39A2 2 0 0 0 9.64 16H19a2 2 0 0 0 2-1.64L23 6H6" />
              </svg>
            </button>
            <span className="absolute -top-1 -right-1 min-w-5 h-5 px-1 rounded-full bg-[#2563EB] text-white text-[11px] leading-5 text-center font-semibold">
              {cartCount}
            </span>
          </div>
        </div>
      </nav>

      <main className="max-w-6xl mx-auto px-4 md:px-6 py-8 md:py-10">
        <div className="mb-6">
          <h2 className="text-2xl font-semibold tracking-tight">
            Mini E-Commerce Store
          </h2>
          <p className="text-sm text-zinc-500 mt-1">
            Browse products and use the built-in support assistant for order
            help.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          {PRODUCTS.map((product) => (
            <article
              key={product.id}
              className="border border-zinc-200 rounded-xl overflow-hidden bg-white"
            >
              <img
                src={product.image}
                alt={product.name}
                className="w-full h-44 object-cover"
              />
              <div className="p-4 space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="text-base font-semibold">{product.name}</h3>
                    <p className="text-xs text-zinc-500">{product.model}</p>
                  </div>
                  <span className="text-xs px-2 py-1 rounded border border-zinc-300 text-zinc-700">
                    {product.stock}
                  </span>
                </div>

                <p className="text-lg font-semibold">
                  {formatInr(product.price)}
                </p>

                <div className="flex gap-2 pt-2">
                  <button
                    onClick={() => addToCart(product)}
                    className="flex-1 border border-zinc-300 rounded-lg px-3 py-2 text-sm font-medium hover:bg-zinc-50 transition-colors"
                  >
                    Add to Cart
                  </button>
                  <button
                    onClick={() => buyNow(product)}
                    className="flex-1 rounded-lg px-3 py-2 text-sm font-medium text-white bg-[#2563EB] hover:bg-blue-700 transition-colors"
                  >
                    Buy Now
                  </button>
                </div>
              </div>
            </article>
          ))}
        </div>
      </main>

      {cartOpen && (
        <>
          <div
            className="fixed inset-0 bg-black/30 z-30"
            onClick={() => setCartOpen(false)}
          />
          <aside className="fixed top-0 right-0 h-full w-full max-w-sm bg-white border-l border-zinc-200 z-40 flex flex-col">
            <div className="h-16 px-4 border-b border-zinc-200 flex items-center justify-between">
              <h3 className="text-base font-semibold">
                Your Cart ({cartCount})
              </h3>
              <button
                onClick={() => setCartOpen(false)}
                className="w-9 h-9 rounded-lg border border-zinc-300 hover:bg-zinc-50"
              >
                ×
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {cart.length === 0 ? (
                <p className="text-sm text-zinc-500">Your cart is empty.</p>
              ) : (
                cart.map((item, idx) => (
                  <div
                    key={`${item.id}-${idx}`}
                    className="border border-zinc-200 rounded-lg p-3"
                  >
                    <div className="flex justify-between gap-2">
                      <div>
                        <p className="text-sm font-semibold">{item.name}</p>
                        <p className="text-xs text-zinc-500">{item.model}</p>
                      </div>
                      <button
                        onClick={() => removeFromCart(idx)}
                        className="text-xs text-zinc-500 hover:text-zinc-800"
                      >
                        Remove
                      </button>
                    </div>
                    <p className="text-sm font-medium mt-2">
                      {formatInr(item.price)}
                    </p>
                  </div>
                ))
              )}
            </div>

            <div className="border-t border-zinc-200 p-4 space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-zinc-600">Total</span>
                <span className="font-semibold">{formatInr(cartTotal)}</span>
              </div>
              <button
                onClick={checkoutCart}
                disabled={cart.length === 0}
                className="w-full rounded-lg px-3 py-2.5 text-sm font-medium text-white bg-[#2563EB] hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Checkout
              </button>
            </div>
          </aside>
        </>
      )}

      {showModal && latestOrder && (
        <div className="fixed inset-0 z-40 bg-black/40 flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-white rounded-xl border border-zinc-200 p-5">
            <h3 className="text-lg font-semibold">Order Placed!</h3>
            <p className="text-sm text-zinc-600 mt-2">
              Your Order ID is{" "}
              <span className="font-semibold text-zinc-900">
                {latestOrder.order_id}
              </span>
              . Estimated delivery: 5-7 business days.
            </p>
            <div className="mt-5 flex justify-end">
              <button
                onClick={() => setShowModal(false)}
                className="px-4 py-2 rounded-lg border border-zinc-300 text-sm font-medium hover:bg-zinc-50"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {orders.length > 0 && (
        <div className="fixed bottom-5 left-5 z-20 hidden md:block">
          <div className="bg-white border border-zinc-200 rounded-lg px-4 py-3 shadow-sm">
            <p className="text-xs text-zinc-500">Latest Order</p>
            <p className="text-sm font-semibold">{orders[0].order_id}</p>
          </div>
        </div>
      )}

      <button
        onClick={() => setChatOpen((v) => !v)}
        className="fixed bottom-5 right-5 z-40 w-14 h-14 rounded-full bg-[#2563EB] text-white shadow-lg flex items-center justify-center hover:bg-blue-700 transition-colors"
        aria-label="Toggle support chat"
      >
        <svg
          width="22"
          height="22"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      </button>

      {chatOpen && (
        <div className="fixed bottom-24 right-5 z-40 w-[92vw] max-w-[400px] h-[70vh] max-h-[500px] bg-white border border-zinc-200 rounded-xl shadow-2xl overflow-hidden">
          <div className="h-full">
            <ChatWindow embedded orderId={latestOrder?.order_id || ""} />
          </div>
        </div>
      )}
    </div>
  );
};

export default ShopEasy;
