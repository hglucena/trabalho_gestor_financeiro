import { useState, useEffect, useCallback } from "react";
import api from "../api/client";
import { useAuth } from "../contexts/AuthContext";
import Modal from "../components/Modal";
import Pagination from "../components/Pagination";

const TRANS_PAGE_SIZE = 20;

function formatMoney(v) {
  return Number(v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export default function PainelConsultor() {
  const { user } = useAuth();
  const [clientes, setClientes] = useState([]);
  const [clienteSel, setClienteSel] = useState(null);
  const [clienteAtualId, setClienteAtualId] = useState(null);
  const [transacoes, setTransacoes] = useState([]);
  const [transPage, setTransPage] = useState(1);
  const [transCount, setTransCount] = useState(0);
  const [contas, setContas] = useState([]);
  const [recomendacoes, setRecomendacoes] = useState([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalTipo, setModalTipo] = useState("");
  const [form, setForm] = useState({});
  const [msg, setMsg] = useState("");

  const loadClientes = useCallback(async () => {
    try {
      const r = await api.get("/consultor/clientes/");
      setClientes(r.data.results || r.data);
    } catch { }
  }, []);

  useEffect(() => { loadClientes(); }, [loadClientes]);

  const loadTransacoesCliente = useCallback(async (clienteId, page = 1) => {
    try {
      const res = await api.get(`/consultor/clientes/${clienteId}/transacoes/?page=${page}&page_size=${TRANS_PAGE_SIZE}`);
      setTransacoes(res.data.results || []);
      setTransCount(res.data.count || 0);
      setTransPage(page);
    } catch { }
  }, []);

  const carregarCliente = async (clienteId) => {
    setClienteSel(clienteId);
    setClienteAtualId(clienteId);
    try {
      const [c, rec] = await Promise.all([
        api.get(`/consultor/clientes/${clienteId}/contas/`),
        api.get("/recomendacoes/"),
      ]);
      loadTransacoesCliente(clienteId, 1);
      setContas(c.data.results || []);
      setRecomendacoes((rec.data.results || []).filter(r => r.cliente === clienteId));
    } catch { }
  };

  const criarRecomendacao = async () => {
    try {
      await api.post("/recomendacoes/", {
        cliente: clienteAtualId,
        texto: form.texto,
      });
      setModalOpen(false);
      setMsg("Recomendação enviada!");
      carregarCliente(clienteAtualId);
    } catch (e) {
      setMsg(e.response?.data?.detail || "Erro ao criar recomendação.");
    }
  };

  return (
    <div>
      <div className="mb-5">
        <h2 className="text-2xl font-bold text-slate-800">Consultoria 🤝</h2>
        <p className="text-sm text-slate-400">Sua carteira de clientes, em modo leitura.</p>
      </div>
      {msg && (
        <div className={msg.includes("Erro") ? "banner-erro" : "banner-ok"}>
          <span className="flex-1">{msg}</span>
          <button onClick={() => setMsg("")} className="font-bold px-1 opacity-60 hover:opacity-100">×</button>
        </div>
      )}

      <div className="tabs">
        <button onClick={() => setClienteSel(null)} className={!clienteSel ? "tab-active" : "tab"}>
          Meus Clientes
        </button>
        {clienteSel && (
          <button className="tab-active">Detalhes do Cliente</button>
        )}
      </div>

      {!clienteSel && (
        <div>
          {clientes.length === 0 ? (
            <div className="card p-10 text-center">
              <p className="text-4xl mb-2">🤝</p>
              <p className="text-slate-400">Nenhum cliente autorizado ainda.</p>
              <p className="text-xs text-slate-400 mt-1">Peça para o cliente autorizar você pelo e-mail na aba "Consultores" do painel dele.</p>
            </div>
          ) : (
            <div className="grid sm:grid-cols-2 gap-4">
              {clientes.map(c => (
                <div key={c.id} className="card-hover p-5 flex items-center gap-4"
                  onClick={() => carregarCliente(c.id)}>
                  <span className="grid place-items-center w-12 h-12 rounded-full bg-gradient-to-br from-indigo-500 to-violet-500 text-white text-sm font-bold shrink-0 shadow-md shadow-indigo-500/25">
                    {(c.nome || "?").split(" ").filter(Boolean).slice(0, 2).map(p => p[0].toUpperCase()).join("")}
                  </span>
                  <div className="min-w-0 flex-1">
                    <h4 className="font-semibold text-slate-800 truncate">{c.nome}</h4>
                    <p className="text-sm text-slate-400 truncate">{c.email}</p>
                  </div>
                  <span className="text-xs font-medium text-indigo-600 shrink-0">Ver finanças →</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {clienteSel && (
        <div>
          <div className="flex flex-wrap gap-1.5 mb-5">
            {["transacoes", "contas", "recomendacoes"].map(k => (
              <button key={k} onClick={() => setClienteSel(c => c ? { ...c, aba: k } : null)}
                className={`text-sm px-3.5 py-1.5 rounded-xl font-medium transition-all ${(clienteSel.aba || "transacoes") === k ? "bg-indigo-100 text-indigo-700 shadow-sm" : "text-slate-500 hover:bg-white hover:text-slate-800"}`}>
                {k === "transacoes" ? "Transações" : k === "contas" ? "Contas" : "Recomendações"}
              </button>
            ))}
          </div>

          {(clienteSel.aba || "transacoes") === "transacoes" && (
            <div className="card overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr><th className="p-3">Descrição</th><th className="p-3">Valor</th><th className="p-3">Tipo</th><th className="p-3">Data</th></tr></thead>
                <tbody>
                  {transacoes.map(t => (
                    <tr key={t.id}>
                      <td className="p-3">{t.descricao || t.tipo}</td>
                      <td className={`p-3 font-semibold tnum ${t.tipo === "despesa" ? "text-red-600" : "text-emerald-600"}`}>{formatMoney(t.valor)}</td>
                      <td className="p-3">{t.tipo === "despesa" ? <span className="badge-red">Despesa</span> : <span className="badge-green">Receita</span>}</td>
                      <td className="p-3">{new Date(t.data).toLocaleDateString("pt-BR")}</td>
                    </tr>
                  ))}
                  {transacoes.length === 0 && <tr><td colSpan={4} className="p-3 text-gray-400 text-center">Nenhuma transação</td></tr>}
                </tbody>
              </table>
              <Pagination page={transPage} pageSize={TRANS_PAGE_SIZE} count={transCount} onPageChange={(p) => loadTransacoesCliente(clienteAtualId, p)} />
            </div>
          )}

          {(clienteSel.aba || "transacoes") === "contas" && (
            <div className="card overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr><th className="p-3">Nome</th><th className="p-3">Saldo Inicial</th><th className="p-3">Ativa</th></tr></thead>
                <tbody>
                  {contas.map(c => (
                    <tr key={c.id}><td className="p-3 font-medium">{c.nome}</td><td className="p-3">{formatMoney(c.saldo_inicial)}</td><td className="p-3">{c.ativa ? "Sim" : "Não"}</td></tr>
                  ))}
                  {contas.length === 0 && <tr><td colSpan={3} className="p-3 text-gray-400 text-center">Nenhuma conta</td></tr>}
                </tbody>
              </table>
            </div>
          )}

          {(clienteSel.aba || "transacoes") === "recomendacoes" && (
            <div>
              <button onClick={() => { setForm({ texto: "" }); setModalTipo("recomendacao"); setModalOpen(true); }}
                className="btn-primary mb-3">
                + Nova Recomendação
              </button>
              <div className="card overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr><th className="p-3">Texto</th><th className="p-3">Data</th></tr></thead>
                  <tbody>
                    {recomendacoes.map(r => (
                      <tr key={r.id}><td className="p-3">{r.texto}</td><td className="p-3">{new Date(r.data).toLocaleDateString("pt-BR")}</td></tr>
                    ))}
                    {recomendacoes.length === 0 && <tr><td colSpan={2} className="p-3 text-gray-400 text-center">Nenhuma recomendação</td></tr>}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title="Nova Recomendação">
        {modalTipo === "recomendacao" && (
          <div className="space-y-3">
            <textarea className="input" rows={4} placeholder="Texto da recomendação..." value={form.texto || ""}
              onChange={e => setForm({ ...form, texto: e.target.value })} />
            <button onClick={criarRecomendacao} className="btn-primary w-full">Enviar</button>
          </div>
        )}
      </Modal>
    </div>
  );
}
