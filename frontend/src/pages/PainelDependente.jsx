import { useState, useEffect, useCallback } from "react";
import api from "../api/client";
import { useAuth } from "../contexts/AuthContext";

function formatMoney(v) {
  return Number(v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export default function PainelDependente() {
  const { user } = useAuth();
  const [mesadas, setMesadas] = useState([]);
  const [transacoes, setTransacoes] = useState([]);
  const [contas, setContas] = useState([]);
  const [categorias, setCategorias] = useState([]);
  const [form, setForm] = useState({ conta: "", categoria: "", valor: "", descricao: "" });
  const [msg, setMsg] = useState("");

  const load = useCallback(async () => {
    try {
      const [m, t, ct, cat] = await Promise.all([
        api.get("/mesadas/"),
        api.get("/transacoes/"),
        api.get("/contas/"),
        api.get("/categorias/"),
      ]);
      setMesadas(m.data.results || []);
      setTransacoes(t.data.results || []);
      setContas(ct.data.results || []);
      setCategorias(cat.data.results || []);
    } catch { }
  }, []);

  useEffect(() => { load(); }, [load]);

  const criarTransacao = async (e) => {
    e.preventDefault();
    setMsg("");
    try {
      await api.post("/transacoes/", {
        conta: Number(form.conta),
        categoria: Number(form.categoria),
        tipo: "despesa",
        valor: form.valor,
        descricao: form.descricao || "Gasto pessoal",
      });
      setForm({ conta: "", categoria: "", valor: "", descricao: "" });
      setMsg("Gasto registrado!");
      load();
    } catch (err) {
      const detail = err.response?.data?.detail || "Erro ao registrar gasto.";
      setMsg(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
  };

  const mesada = mesadas[0];

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">Minha Mesada — {user?.nome}</h2>

      {msg && (
        <div className={`p-2 rounded text-sm mb-3 ${msg.includes("Erro") || msg.includes("limite") || msg.includes("Gasto acima") ? "bg-red-100 text-red-800" : "bg-green-100 text-green-800"}`}>
          {msg}
        </div>
      )}

      {mesada ? (
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-gray-500">Grupo</p>
              <p className="font-semibold">{mesada.nome_grupo}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Valor da Mesada</p>
              <p className="font-semibold text-indigo-600">{formatMoney(mesada.valor)}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Saldo Disponível</p>
              <p className={`font-bold text-lg ${Number(mesada.saldo_atual) > 0 ? "text-green-600" : "text-red-600"}`}>
                {formatMoney(mesada.saldo_atual)}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Recarga</p>
              <p className="font-semibold capitalize">{mesada.periodo_recarga}</p>
            </div>
          </div>
        </div>
      ) : (
        <p className="text-gray-400 mb-6">Nenhuma mesada configurada para você.</p>
      )}

      <div className="grid md:grid-cols-2 gap-6">
        <div>
          <h3 className="font-semibold mb-3">Novo Gasto</h3>
          <form onSubmit={criarTransacao} className="bg-white rounded-lg shadow p-4 space-y-3">
            <select className="w-full border rounded px-3 py-2 text-sm" value={form.conta} onChange={e => setForm({ ...form, conta: e.target.value })} required>
              <option value="">Conta</option>
              {contas.map(c => <option key={c.id} value={c.id}>{c.nome}</option>)}
            </select>
            <select className="w-full border rounded px-3 py-2 text-sm" value={form.categoria} onChange={e => setForm({ ...form, categoria: e.target.value })} required>
              <option value="">Categoria</option>
              {categorias.map(c => <option key={c.id} value={c.id}>{c.nome}</option>)}
            </select>
            <input className="w-full border rounded px-3 py-2 text-sm" type="number" step="0.01" placeholder="Valor (R$)" value={form.valor}
              onChange={e => setForm({ ...form, valor: e.target.value })} required />
            <input className="w-full border rounded px-3 py-2 text-sm" placeholder="Descrição" value={form.descricao}
              onChange={e => setForm({ ...form, descricao: e.target.value })} />
            <button type="submit" className="w-full bg-indigo-600 text-white rounded-lg py-2 text-sm hover:bg-indigo-700">
              Registrar Gasto
            </button>
          </form>
        </div>

        <div>
          <h3 className="font-semibold mb-3">Meus Gastos</h3>
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50"><tr><th className="p-3">Descrição</th><th className="p-3">Valor</th><th className="p-3">Data</th></tr></thead>
              <tbody>
                {transacoes.filter(t => t.tipo === "despesa").map(t => (
                  <tr key={t.id} className="border-t">
                    <td className="p-3">{t.descricao || "Gasto"}</td>
                    <td className="p-3 text-red-600 font-medium">{formatMoney(t.valor)}</td>
                    <td className="p-3">{new Date(t.data).toLocaleDateString("pt-BR")}</td>
                  </tr>
                ))}
                {transacoes.filter(t => t.tipo === "despesa").length === 0 && (
                  <tr><td colSpan={3} className="p-3 text-gray-400 text-center">Nenhum gasto registrado.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
