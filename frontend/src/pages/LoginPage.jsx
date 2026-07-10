import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const usuario = await login(email, password);
      navigate(usuario.papel_sistema === "admin" ? "/admin" : "/painel");
    } catch (err) {
      setError(err.response?.data?.non_field_errors?.[0] || "Email ou senha inválidos.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-600 to-indigo-800">
      <div className="bg-white rounded-xl shadow-2xl p-8 w-full max-w-sm">
        <h1 className="text-2xl font-bold text-center text-indigo-700 mb-6">NossoBolso</h1>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              required placeholder="seu@email.com" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Senha</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              required placeholder="Sua senha" />
          </div>
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <button type="submit" disabled={loading}
            className="w-full bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg py-2 text-sm font-medium disabled:opacity-50">
            {loading ? "Entrando..." : "Entrar"}
          </button>
        </form>
        <p className="text-center text-sm text-gray-500 mt-4">
          Não tem conta? <Link to="/cadastro" className="text-indigo-600 hover:underline">Cadastre-se</Link>
        </p>
      </div>
    </div>
  );
}
