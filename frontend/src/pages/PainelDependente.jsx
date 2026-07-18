import { useState, useEffect, useCallback } from "react";
import api from "../api/client";
import { useAuth } from "../contexts/AuthContext";
import Pagination from "../components/Pagination";

const TRANS_PAGE_SIZE = 20;

function formatMoney(v) {
  return Number(v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export default function PainelDependente() {
  const { user } = useAuth();
  const [mesadas, setMesadas] = useState([]);
  const [transacoes, setTransacoes] = useState([]);
  const [transPage, setTransPage] = useState(1);
  const [transCount, setTransCount] = useState(0);
  const [contas, setContas] = useState([]);
  const [categorias, setCategorias] = useState([]);
  const [metas, setMetas] = useState([]);
  const [form, setForm] = useState({ conta: "", categoria: "", valor: "", descricao: "" });
  const [formMeta, setFormMeta] = useState({ nome: "", valor_alvo: "" });
  const [msg, setMsg] = useState("");

  const load = useCallback(async () => {
    try {
      const [m, ct, cat, mt] = await Promise.all([
        api.get("/mesadas/"),
        api.get("/contas/"),
        api.get("/categorias/"),
        api.get("/metas/"),
      ]);
      setMesadas(m.data.results || []);
      setContas(ct.data.results || []);
      setCategorias(cat.data.results || []);
      setMetas(mt.data.results || []);
    } catch { }
  }, []);

  const loadTransacoes = useCallback(async (page = 1) => {
    try {
      const res = await api.get(`/transacoes/?page=${page}&page_size=${TRANS_PAGE_SIZE}`);
      setTransacoes(res.data.results || []);
      setTransCount(res.data.count || 0);
      setTransPage(page);
    } catch { }
  }, []);

  useEffect(() => { load(); loadTransacoes(1); }, [load, loadTransacoes]);

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
      loadTransacoes(1);
    } catch (err) {
      const detail = err.response?.data?.detail || "Erro ao registrar gasto.";
      setMsg(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
  };

  const criarMeta = async (e) => {
    e.preventDefault();
    setMsg("");
    try {
      await api.post("/metas/", { nome: formMeta.nome, valor_alvo: formMeta.valor_alvo });
      setFormMeta({ nome: "", valor_alvo: "" });
      setMsg("Meta criada! Guarde um pouco da mesada nela.");
      load();
    } catch (err) {
      const detail = err.response?.data?.detail || "Erro ao criar a meta.";
      setMsg(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
  };

  const guardarNaMeta = async (meta) => {
    const valor = prompt(`Quanto da sua mesada você quer guardar para "${meta.nome}"?`);
    if (!valor) return;
    setMsg("");
    try {
      await api.post(`/metas/${meta.id}/aportar/`, { valor });
      setMsg(`Guardado em "${meta.nome}"! O valor saiu do saldo da mesada.`);
      load();
      loadTransacoes(1);
    } catch (err) {
      const detail = err.response?.data?.detail || "Erro ao guardar.";
      setMsg(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
  };

  const mesada = mesadas.find(m => m.dependente === user?.id) || mesadas[0];

  return (
    <div>
      <div className="mb-5">
        <h2 className="text-2xl font-bold text-slate-800">Minha Mesada 🐷</h2>
        <p className="text-sm text-slate-400">Acompanhe seu saldo, registre gastos e junte para o que você quer.</p>
      </div>

      {msg && (
        <div className={msg.includes("Erro") || msg.includes("limite") || msg.includes("acima") ? "banner-erro" : "banner-ok"}>
          <span className="flex-1">{msg}</span>
          <button onClick={() => setMsg("")} className="font-bold px-1 opacity-60 hover:opacity-100">×</button>
        </div>
      )}

      {mesada ? (
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-indigo-600 via-indigo-600 to-violet-600 text-white shadow-xl shadow-indigo-600/25 p-6 md:p-8 mb-8">
          <div className="absolute -top-16 -right-16 w-56 h-56 rounded-full bg-white/10 blur-2xl" />
          <div className="absolute -bottom-20 -left-10 w-48 h-48 rounded-full bg-violet-300/20 blur-2xl" />
          <div className="relative flex flex-wrap items-end justify-between gap-6">
            <div>
              <p className="text-indigo-200 text-sm font-medium">Saldo disponível · {mesada.nome_grupo}</p>
              <p className={`text-4xl md:text-5xl font-extrabold tnum mt-1 ${Number(mesada.saldo_atual) <= 0 ? "text-red-200" : ""}`}>
                {formatMoney(mesada.saldo_atual)}
              </p>
              <p className="text-indigo-200 text-xs mt-2">
                Mesada de <span className="font-semibold text-white">{formatMoney(mesada.valor)}</span> · recarga {mesada.periodo_recarga}
                {mesada.ultima_recarga && (() => {
                  const dias = { semanal: 7, quinzenal: 15, mensal: 30 }[mesada.periodo_recarga] || 30;
                  const proxima = new Date(new Date(mesada.ultima_recarga).getTime() + dias * 86400000);
                  return <> · próxima em <span className="font-semibold text-white">{proxima.toLocaleDateString("pt-BR")}</span></>;
                })()}
              </p>
            </div>
            <div className="w-full md:w-64">
              <div className="flex justify-between text-[11px] text-indigo-200 mb-1">
                <span>Quanto ainda tenho</span>
                <span className="tnum">{Math.max(0, Math.min(100, Math.round(Number(mesada.saldo_atual) / Number(mesada.valor) * 100)))}%</span>
              </div>
              <div className="w-full bg-white/20 rounded-full h-2.5 overflow-hidden">
                <div className="h-full rounded-full bg-white transition-[width] duration-700 ease-out"
                  style={{ width: `${Math.max(0, Math.min(100, Number(mesada.saldo_atual) / Number(mesada.valor) * 100))}%` }} />
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="card p-10 text-center mb-8">
          <p className="text-4xl mb-2">🐷</p>
          <p className="text-slate-400">Nenhuma mesada configurada para você ainda.</p>
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-6">
        <div>
          <h3 className="font-semibold mb-3">Novo Gasto</h3>
          <form onSubmit={criarTransacao} className="card p-4 space-y-3">
            <select className="input" value={form.conta} onChange={e => setForm({ ...form, conta: e.target.value })} required>
              <option value="">Conta</option>
              {contas.map(c => <option key={c.id} value={c.id}>{c.nome}</option>)}
            </select>
            <select className="input" value={form.categoria} onChange={e => setForm({ ...form, categoria: e.target.value })} required>
              <option value="">Categoria</option>
              {categorias.map(c => <option key={c.id} value={c.id}>{c.nome}</option>)}
            </select>
            <input className="input" type="number" step="0.01" placeholder="Valor (R$)" value={form.valor}
              onChange={e => setForm({ ...form, valor: e.target.value })} required />
            <input className="input" placeholder="Descrição" value={form.descricao}
              onChange={e => setForm({ ...form, descricao: e.target.value })} />
            <button type="submit" className="btn-primary w-full">
              Registrar Gasto
            </button>
          </form>
        </div>

        <div>
          <h3 className="font-semibold mb-3">Meus Gastos</h3>
          <div className="card overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr><th className="p-3">Descrição</th><th className="p-3">Valor</th><th className="p-3">Data</th></tr></thead>
              <tbody>
                {transacoes.filter(t => t.tipo === "despesa").map(t => (
                  <tr key={t.id}>
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
            <Pagination page={transPage} pageSize={TRANS_PAGE_SIZE} count={transCount} onPageChange={loadTransacoes} />
          </div>
        </div>
      </div>

      {/* Metas do dependente */}
      <div className="mt-8">
        <h3 className="font-semibold text-slate-800 mb-3">Minhas Metas 🎯</h3>
        <div className="grid md:grid-cols-2 gap-4">
          {metas.map(m => (
            <div key={m.id} className="card p-5">
              <div className="flex items-center justify-between mb-1">
                <h4 className="font-semibold text-slate-800">{m.nome}</h4>
                {m.concluida && <span className="badge-green">✓ consegui!</span>}
              </div>
              <p className="text-sm text-slate-400 mb-2 tnum">{formatMoney(m.valor_atual)} de {formatMoney(m.valor_alvo)}</p>
              <div className="progress-track mb-3">
                <div className={`progress-fill ${m.concluida ? "bg-emerald-500" : "bg-gradient-to-r from-indigo-500 to-violet-500"}`} style={{ width: `${m.percentual}%` }} />
              </div>
              <div className="flex items-center justify-between">
                {!m.concluida ? (
                  <button onClick={() => guardarNaMeta(m)} className="btn-primary text-xs px-3 py-1.5">
                    + Guardar da mesada
                  </button>
                ) : <span className="text-2xl">🎉</span>}
                <span className="text-xs font-semibold text-slate-400 tnum">{m.percentual}%</span>
              </div>
            </div>
          ))}
          <form onSubmit={criarMeta} className="rounded-2xl p-5 border-2 border-dashed border-indigo-200 bg-indigo-50/40 space-y-2.5 transition-colors hover:border-indigo-300">
            <p className="text-sm font-semibold text-slate-600">✨ Nova meta (ex.: PS5, bicicleta...)</p>
            <input className="input" placeholder="O que você quer comprar?" value={formMeta.nome}
              onChange={e => setFormMeta({ ...formMeta, nome: e.target.value })} required />
            <input className="input" type="number" step="0.01" min="0.01" placeholder="Quanto custa? (R$)" value={formMeta.valor_alvo}
              onChange={e => setFormMeta({ ...formMeta, valor_alvo: e.target.value })} required />
            <button type="submit" className="btn-primary w-full">
              Criar Meta
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
