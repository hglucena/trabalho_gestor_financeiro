import { useEffect, useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./contexts/AuthContext";
import Layout from "./components/Layout";
import PrivateRoute from "./components/PrivateRoute";
import LoginPage from "./pages/LoginPage";
import CadastroPage from "./pages/CadastroPage";
import PainelMembro from "./pages/PainelMembro";
import PainelGestor from "./pages/PainelGestor";
import PainelAdmin from "./pages/PainelAdmin";
import PainelDependente from "./pages/PainelDependente";
import PainelConsultor from "./pages/PainelConsultor";
import api from "./api/client";

function PainelDispatcher() {
  const { user } = useAuth();
  const [temMesada, setTemMesada] = useState(null);

  useEffect(() => {
    if (user?.papel_sistema === "admin") return;
    // dependente = tem mesada PRÓPRIA (gestor também enxerga mesadas, mas dos dependentes do grupo)
    api.get("/mesadas/")
      .then(r => setTemMesada((r.data.results || []).some(m => m.dependente === user?.id)))
      .catch(() => setTemMesada(false));
  }, [user]);

  if (user?.papel_sistema === "admin") return <PainelAdmin />;
  if (temMesada === null) return <p className="text-gray-400 text-center py-10">Carregando...</p>;
  if (temMesada) return <PainelDependente />;
  return <PainelMembro />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/cadastro" element={<CadastroPage />} />
      <Route path="/painel" element={<PrivateRoute><Layout /></PrivateRoute>}>
        <Route index element={<PainelDispatcher />} />
        <Route path="gestor" element={<PainelGestor />} />
        <Route path="dependente" element={<PainelDependente />} />
        <Route path="consultor" element={<PainelConsultor />} />
      </Route>
      <Route path="/admin" element={<PrivateRoute><Layout /></PrivateRoute>}>
        <Route index element={<PainelAdmin />} />
      </Route>
      <Route path="*" element={<Navigate to="/painel" replace />} />
    </Routes>
  );
}
