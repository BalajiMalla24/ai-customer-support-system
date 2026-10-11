import { useState } from "react";
import "./App.css";
import AdminDashboard from "./components/AdminDashboard";
import ChatWindow from "./components/ChatWindow";
import MyOrders from "./components/MyOrders";
import ShopEasy from "./components/ShopEasy";
import VoiceMode from "./components/VoiceMode";

const sessionFromOrder = (orderId) =>
  `order-${String(orderId || "general").toUpperCase()}`;

function App() {
  const [view, setView] = useState("store");
  const [selectedOrderId, setSelectedOrderId] = useState("");

  const openOrderSupport = (orderId, target = "chat") => {
    setSelectedOrderId(String(orderId || "").toUpperCase());
    setView(target);
  };

  const clearOrderContext = () => {
    setSelectedOrderId("");
    setView("chat");
  };

  const orderSessionId = selectedOrderId
    ? sessionFromOrder(selectedOrderId)
    : undefined;

  return (
    <div className="flex h-screen bg-white font-sans overflow-hidden">
      {/* Sidebar (ChatGPT style) */}
      <div className="w-[260px] bg-[#F9F9F9] flex-shrink-0 flex-col border-r border-[#ececec] hidden md:flex">
        <div className="p-4 flex flex-col gap-2 flex-1">
          <button
            onClick={() => setView("store")}
            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-[14px] font-medium transition-colors ${
              view === "store"
                ? "bg-[#ececec] text-gray-900"
                : "text-gray-600 hover:bg-[#f3f3f3] hover:text-gray-900"
            }`}
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
              <path d="M3 3h2l.4 2M7 13h10l4-8H5.4" />
              <circle cx="7" cy="21" r="1" />
              <circle cx="17" cy="21" r="1" />
            </svg>
            Store
          </button>

          <button
            onClick={() => setView("orders")}
            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-[14px] font-medium transition-colors ${
              view === "orders"
                ? "bg-[#ececec] text-gray-900"
                : "text-gray-600 hover:bg-[#f3f3f3] hover:text-gray-900"
            }`}
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
              <path d="M9 11l3 3L22 4" />
              <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
            </svg>
            My Orders
          </button>

          <button
            onClick={() => setView("chat")}
            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-[14px] font-medium transition-colors ${
              view === "chat"
                ? "bg-[#ececec] text-gray-900"
                : "text-gray-600 hover:bg-[#f3f3f3] hover:text-gray-900"
            }`}
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
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
            Customer Support
          </button>

          <button
            onClick={() => setView("voice")}
            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-[14px] font-medium transition-colors ${
              view === "voice"
                ? "bg-[#ececec] text-gray-900"
                : "text-gray-600 hover:bg-[#f3f3f3] hover:text-gray-900"
            }`}
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
              <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" x2="12" y1="19" y2="22" />
            </svg>
            Voice Mode
          </button>

          <button
            onClick={() => setView("admin")}
            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-[14px] font-medium transition-colors ${
              view === "admin"
                ? "bg-[#ececec] text-gray-900"
                : "text-gray-600 hover:bg-[#f3f3f3] hover:text-gray-900"
            }`}
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
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              <line x1="3" y1="9" x2="21" y2="9" />
              <line x1="9" y1="21" x2="9" y2="9" />
            </svg>
            Admin Portal
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-full bg-white relative overflow-hidden">
        {/* Mobile Header Toggle */}
        <div className="md:hidden flex items-center p-3 border-b border-[#ececec] bg-[#F9F9F9]">
          <select
            value={view}
            onChange={(e) => setView(e.target.value)}
            className="bg-transparent text-[14px] font-medium text-gray-900 outline-none w-full"
          >
            <option value="store">Store</option>
            <option value="orders">My Orders</option>
            <option value="chat">Customer Support</option>
            <option value="voice">Voice Mode</option>
            <option value="admin">Admin Portal</option>
          </select>
        </div>

        <div
          className={
            view === "store"
              ? "flex-1 overflow-y-auto"
              : "flex-1 overflow-hidden"
          }
        >
          {view === "store" ? (
            <ShopEasy onOpenOrderSupport={openOrderSupport} />
          ) : view === "orders" ? (
            <MyOrders
              onOpenOrderSupport={openOrderSupport}
              selectedOrderId={selectedOrderId}
            />
          ) : view === "chat" ? (
            <ChatWindow
              forcedSessionId={orderSessionId}
              orderId={selectedOrderId || undefined}
              onClearOrderContext={clearOrderContext}
            />
          ) : view === "voice" ? (
            <VoiceMode
              forcedSessionId={orderSessionId}
              orderId={selectedOrderId || undefined}
            />
          ) : (
            <AdminDashboard />
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
