import { useEffect, useMemo, useState } from "react";

const normalizeOrderId = (value) =>
  String(value || "")
    .trim()
    .toUpperCase();

const statusTone = (status) => {
  const value = String(status || "").toLowerCase();
  if (value.includes("deliver")) return "text-emerald-700 bg-emerald-50";
  if (value.includes("transit") || value.includes("ship")) {
    return "text-blue-700 bg-blue-50";
  }
  if (value.includes("delay") || value.includes("hold")) {
    return "text-amber-700 bg-amber-50";
  }
  return "text-zinc-700 bg-zinc-100";
};

const formatInr = (amount) =>
  `Rs. ${Number.isFinite(Number(amount)) ? Number(amount).toLocaleString("en-IN") : amount}`;

const MyOrders = ({ onOpenOrderSupport, selectedOrderId }) => {
  const [orders, setOrders] = useState([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedOrder, setSelectedOrder] = useState("");
  const [events, setEvents] = useState([]);
  const [eventsLoading, setEventsLoading] = useState(false);

  useEffect(() => {
    const loadOrders = async () => {
      try {
        setLoading(true);
        setError("");
        const res = await fetch(
          "http://localhost:8000/api/mock/orders?limit=120",
        );
        const data = await res.json();
        const rows = Array.isArray(data?.orders) ? data.orders : [];
        setOrders(rows);
        if (rows.length > 0) {
          const first = normalizeOrderId(selectedOrderId || rows[0].order_id);
          setSelectedOrder(first);
        }
      } catch (e) {
        setError("Unable to load orders right now.");
      } finally {
        setLoading(false);
      }
    };

    loadOrders();
  }, [selectedOrderId]);

  useEffect(() => {
    const id = normalizeOrderId(selectedOrder || selectedOrderId);
    if (!id) {
      setEvents([]);
      return;
    }

    const loadEvents = async () => {
      try {
        setEventsLoading(true);
        const res = await fetch(
          `http://localhost:8000/api/mock/order/${id}/events`,
        );
        const data = await res.json();
        setEvents(Array.isArray(data?.events) ? data.events : []);
      } catch {
        setEvents([]);
      } finally {
        setEventsLoading(false);
      }
    };

    loadEvents();
  }, [selectedOrder, selectedOrderId]);

  const filteredOrders = useMemo(() => {
    const q = normalizeOrderId(query);
    if (!q) return orders;
    return orders.filter((o) => {
      const orderId = normalizeOrderId(o.order_id);
      const customer = normalizeOrderId(o.customer || o.customer_name);
      const item = normalizeOrderId(o.item || o.product_name);
      return orderId.includes(q) || customer.includes(q) || item.includes(q);
    });
  }, [orders, query]);

  const activeOrder = useMemo(() => {
    const id = normalizeOrderId(selectedOrder || selectedOrderId);
    return filteredOrders.find((o) => normalizeOrderId(o.order_id) === id);
  }, [filteredOrders, selectedOrder, selectedOrderId]);

  const openSupport = (orderId, target) => {
    if (typeof onOpenOrderSupport === "function") {
      onOpenOrderSupport(orderId, target);
    }
  };

  return (
    <div className="w-full h-full bg-[#fafafa] overflow-y-auto">
      <div className="max-w-6xl mx-auto px-4 md:px-8 py-8 space-y-6">
        <div className="bg-white border border-zinc-200 rounded-2xl p-5 md:p-6">
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-900">
            My Orders
          </h1>
          <p className="text-sm text-zinc-500 mt-1">
            Search any order ID and load support chat by that exact order
            context.
          </p>
          <div className="mt-4 grid grid-cols-1 md:grid-cols-[1fr_auto_auto] gap-3">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by order ID, product, or customer"
              className="w-full rounded-xl border border-zinc-300 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-200"
            />
            <button
              onClick={() =>
                selectedOrder && openSupport(selectedOrder, "chat")
              }
              disabled={!selectedOrder}
              className="rounded-xl px-4 py-2.5 text-sm font-medium text-white bg-[#2563EB] hover:bg-blue-700 disabled:opacity-50"
            >
              Open Chat for Order
            </button>
            <button
              onClick={() =>
                selectedOrder && openSupport(selectedOrder, "voice")
              }
              disabled={!selectedOrder}
              className="rounded-xl px-4 py-2.5 text-sm font-medium border border-zinc-300 hover:bg-zinc-50 disabled:opacity-50"
            >
              Open Voice for Order
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-[1.35fr_1fr] gap-5">
          <section className="bg-white border border-zinc-200 rounded-2xl p-4 md:p-5">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-zinc-800">
                Order List
              </h2>
              <span className="text-xs text-zinc-500">
                {filteredOrders.length} items
              </span>
            </div>
            <div className="max-h-[520px] overflow-y-auto pr-1 space-y-3">
              {loading ? (
                <p className="text-sm text-zinc-500">Loading orders...</p>
              ) : error ? (
                <p className="text-sm text-rose-600">{error}</p>
              ) : filteredOrders.length === 0 ? (
                <p className="text-sm text-zinc-500">
                  No orders matched your search.
                </p>
              ) : (
                filteredOrders.map((order) => {
                  const orderId = normalizeOrderId(order.order_id);
                  const isActive =
                    normalizeOrderId(selectedOrder || selectedOrderId) ===
                    orderId;
                  const quantity = Number(order.quantity || 1);
                  const unitPrice = Number(order.price || 0);
                  const subtotal = Number(
                    order.subtotal || unitPrice * quantity,
                  );

                  return (
                    <button
                      key={orderId}
                      onClick={() => setSelectedOrder(orderId)}
                      className={`w-full text-left rounded-xl border p-4 transition-colors ${
                        isActive
                          ? "border-blue-300 bg-blue-50/50"
                          : "border-zinc-200 bg-white hover:bg-zinc-50"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-xs font-mono text-zinc-500">
                            {orderId}
                          </p>
                          <p className="text-sm font-semibold text-zinc-900 mt-1">
                            {order.item || order.product_name || "Product"}
                          </p>
                          <p className="text-xs text-zinc-500 mt-1">
                            {order.customer ||
                              order.customer_name ||
                              "Customer"}
                          </p>
                        </div>
                        <span
                          className={`text-xs px-2 py-1 rounded-full ${statusTone(order.status)}`}
                        >
                          {order.status || "Unknown"}
                        </span>
                      </div>
                      <div className="mt-3 grid grid-cols-3 gap-2 text-xs text-zinc-600">
                        <p>Qty: {quantity}</p>
                        <p>Unit: {formatInr(unitPrice)}</p>
                        <p className="font-semibold text-zinc-800">
                          Total: {formatInr(subtotal)}
                        </p>
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </section>

          <section className="bg-white border border-zinc-200 rounded-2xl p-4 md:p-5">
            <h2 className="text-sm font-semibold text-zinc-800">
              Order Timeline
            </h2>
            {!activeOrder ? (
              <p className="text-sm text-zinc-500 mt-3">
                Select an order to view events.
              </p>
            ) : (
              <>
                <div className="mt-3 p-3 rounded-xl border border-zinc-200 bg-zinc-50">
                  <p className="text-xs text-zinc-500">Active Order</p>
                  <p className="text-sm font-semibold text-zinc-900 mt-1">
                    {normalizeOrderId(activeOrder.order_id)}
                  </p>
                  <p className="text-xs text-zinc-600 mt-1">
                    Estimated Delivery:{" "}
                    {activeOrder.estimated_delivery || "Not available"}
                  </p>
                </div>

                <div className="mt-4 space-y-3 max-h-[410px] overflow-y-auto pr-1">
                  {eventsLoading ? (
                    <p className="text-sm text-zinc-500">
                      Loading event history...
                    </p>
                  ) : events.length === 0 ? (
                    <p className="text-sm text-zinc-500">
                      No event history available.
                    </p>
                  ) : (
                    events.map((ev, idx) => (
                      <div
                        key={`${ev.timestamp || "ts"}-${idx}`}
                        className="rounded-lg border border-zinc-200 p-3"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <p className="text-sm font-semibold text-zinc-800">
                            {ev.status || "Status Update"}
                          </p>
                          <span className="text-[11px] text-zinc-500">
                            {ev.timestamp
                              ? new Date(ev.timestamp).toLocaleString()
                              : "Unknown time"}
                          </span>
                        </div>
                        <p className="text-xs text-zinc-600 mt-1">
                          {ev.note || "No additional note"}
                        </p>
                      </div>
                    ))
                  )}
                </div>
              </>
            )}
          </section>
        </div>
      </div>
    </div>
  );
};

export default MyOrders;
