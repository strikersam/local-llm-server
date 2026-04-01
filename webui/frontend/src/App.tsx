import { Navigate, Route, Routes } from "react-router-dom";
import ChatApp from "./pages/ChatApp";
import AdminApp from "./pages/AdminApp";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/app" replace />} />
      <Route path="/app" element={<ChatApp />} />
      <Route path="/app/*" element={<ChatApp />} />
      <Route path="/admin/app" element={<AdminApp />} />
      <Route path="/admin/app/*" element={<AdminApp />} />
      <Route path="*" element={<Navigate to="/app" replace />} />
    </Routes>
  );
}

