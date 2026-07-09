import { useEffect, useState } from "react";
import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import api from "../api/client";

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [temMesada, setTemMesada] = useState(false);
  const [temConsultoria, setTemConsultoria] = useState(false);

  useEffect(() => {
    if (user?.papel_sistema === "admin") return;
    api.get("/mesadas/")
      .then(r => setTemMesada((r.data.results || []).length > 0))
      .catch(() => {});
    api.get("/consultor/clientes/")
      .then(r => setTemConsultoria((r.data.results || r.data || []).length > 0))
      .catch(() => {});
  }, [user]);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen flex flex-col">
      <nav className="bg-indigo-700 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 flex items-center justify-between h-14">
          <div className="flex items-center gap-6">
            <span className="font-bold text-lg">Finanças Compartilhadas</span>
            <NavLink to="/painel" className={({ isActive }) => `text-sm hover:text-indigo-200 ${isActive ? "underline" : ""}`}>
              Painel
            </NavLink>
            {temMesada && (
              <NavLink to="/painel/dependente" className={({ isActive }) => `text-sm hover:text-indigo-200 ${isActive ? "underline" : ""}`}>
                Mesada
              </NavLink>
            )}
            {temConsultoria && (
              <NavLink to="/painel/consultor" className={({ isActive }) => `text-sm hover:text-indigo-200 ${isActive ? "underline" : ""}`}>
                Consultoria
              </NavLink>
            )}
            {user?.papel_sistema === "admin" && (
              <NavLink to="/admin" className={({ isActive }) => `text-sm hover:text-indigo-200 ${isActive ? "underline" : ""}`}>
                Admin
              </NavLink>
            )}
          </div>
          <div className="flex items-center gap-3 text-sm">
            <span>{user?.nome}</span>
            <span className="text-indigo-300 text-xs">({user?.papel_sistema})</span>
            <button onClick={handleLogout} className="bg-indigo-600 hover:bg-indigo-500 px-3 py-1 rounded text-xs">
              Sair
            </button>
          </div>
        </div>
      </nav>
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
