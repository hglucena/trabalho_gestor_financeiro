import { useState, useEffect, useCallback } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from "recharts";
import api from "../api/client";
import { extrairErro } from "../api/erros";
import { useAuth } from "../contexts/AuthContext";
import Modal from "../components/Modal";

function formatMoney(v) {
  return Number(v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export default function PainelGestor() {
  const { user } = useAuth();
  const [aba, setAba] = useState("grupos");
  const [grupos, setGrupos] = useState([]);
  const [grupoSel, setGrupoSel] = useState(null);
  const [membros, setMembros] = useState([]);
  const [mesadas, setMesadas] = useState([]);
  const [quemDeve, setQuemDeve] = useState([]);
  const [orcResumo, setOrcResumo] = useState([]);
  const [transacoes, setTransacoes] = useState([]);
  const [categorias, setCategorias] = useState([]);
  const [contas, setContas] = useState([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalTipo, setModalTipo] = useState("");
  const [form, setForm] = useState({});
  const [msg, setMsg] = useState("");

  const loadGrupos = useCallback(async () => {
    try { const r = await api.get("/grupos/"); setGrupos(r.data.results || []); } catch { }
  }, []);

  useEffect(() => { loadGrupos(); }, [loadGrupos]);
  useEffect(() => { api.get("/categorias/").then(r => setCategorias(r.data.results || [])).catch(() => {}); }, []);
  useEffect(() => { api.get("/contas/").then(r => setContas(r.data.results || [])).catch(() => {}); }, []);

  const carregarGrupo = async (gid) => {
    setGrupoSel(gid);
    setAba("membros");
    try {
      const [mr, t, ms] = await Promise.all([
        api.get(`/grupos/${gid}/membros/`),
        api.get(`/transacoes/?grupo=${gid}&page_size=200`),
        api.get("/mesadas/"),
      ]);
      setMembros(mr.data.results || []);
      setTransacoes(t.data.results || []);
      setMesadas((ms.data.results || []).filter(m => m.grupo === gid));
      const q = await api.get(`/grupos/${gid}/quem_deve_a_quem/`);
      setQuemDeve(q.data.membros || []);
      const o = await api.get(`/grupos/${gid}/orcamento_resumo/`);
      setOrcResumo(o.data.orcamentos || []);
    } catch { }
  };

  const criarMesada = async () => {
    try {
      await api.post("/mesadas/", {
        dependente: Number(form.dependente),
        grupo: grupoSel,
        valor: form.valor,
        periodo_recarga: form.periodo_recarga || "mensal",
      });
      setModalOpen(false);
      setMsg("Mesada criada!");
      carregarGrupo(grupoSel);
    } catch (e) {
      setMsg("Erro: " + extrairErro(e, "não foi possível criar a mesada."));
    }
  };

  const recarregarMesada = async (mesada) => {
    const valor = prompt(
      `Recarregar a mesada de ${mesada.nome_dependente}. Valor (deixe em branco para ${formatMoney(mesada.valor)}):`
    );
    if (valor === null) return;
    try {
      await api.post(`/mesadas/${mesada.id}/recarregar/`, valor ? { valor } : {});
      setMsg("Mesada recarregada!");
      carregarGrupo(grupoSel);
    } catch (e) {
      setMsg("Erro: " + extrairErro(e, "não foi possível recarregar."));
    }
  };

  const criarGrupo = async () => {
    try {
      await api.post("/grupos/", form);
      setModalOpen(false);
      setMsg("Grupo criado!");
      loadGrupos();
    } catch (e) {
      setMsg("Erro ao criar grupo.");
    }
  };

  const adicionarMembro = async () => {
    try {
      await api.post(`/grupos/${grupoSel}/membros/`, { usuario: Number(form.usuario_id) });
      setModalOpen(false);
      carregarGrupo(grupoSel);
    } catch (e) {
      setMsg("Erro ao adicionar membro.");
    }
  };

  // dependentes ficam fora do rateio — eles têm a própria mesada
  const membrosDivisao = membros.filter(m => m.papel_no_grupo !== "dependente");

  const dividirDespesa = async () => {
    try {
      const data = {
        conta: form.conta,
        categoria: form.categoria,
        tipo: "despesa",
        valor: form.valor,
        descricao: form.descricao || "Despesa do grupo",
        grupo: grupoSel,
      };
      if (form.modo === "igual") {
        data.dividir_igualmente = true;
        data.participantes_ids = membrosDivisao.map(m => m.usuario);
      } else {
        data.divisoes = membrosDivisao
          .map(m => ({ participante: m.usuario, valor_devido: form.divisoes?.[m.usuario] }))
          .filter(d => Number(d.valor_devido) > 0);
      }
      await api.post("/transacoes/", data);
      setModalOpen(false);
      carregarGrupo(grupoSel);
      setMsg("Despesa dividida com sucesso!");
    } catch (e) {
      setMsg("Erro: " + extrairErro(e, "não foi possível dividir a despesa."));
    }
  };

  const abas = [
    { key: "grupos", label: "Meus Grupos" },
    { key: "detalhe", label: "Detalhes do Grupo", disabled: !grupoSel },
  ];
  const abasDetalhe = ["detalhe", "membros", "transacoes", "quemdeve", "orcamento", "mesadas"];

  return (
    <div>
      <div className="mb-5">
        <h2 className="text-2xl font-bold text-slate-800">Grupos 👥</h2>
        <p className="text-sm text-slate-400">Administre os grupos, divida despesas e acompanhe quem deve a quem.</p>
      </div>
      {msg && (
        <div className={msg.startsWith("Erro") ? "banner-erro" : "banner-ok"}>
          <span className="flex-1">{msg}</span>
          <button onClick={() => setMsg("")} className="font-bold px-1 opacity-60 hover:opacity-100">×</button>
        </div>
      )}

      <div className="tabs">
        {abas.map(a => {
          const ativa = a.key === "grupos" ? aba === "grupos" : abasDetalhe.includes(aba);
          return (
            <button key={a.key} onClick={() => a.key === "grupos" ? setAba("grupos") : grupoSel && setAba("membros")}
              className={`${ativa ? "tab-active" : "tab"} ${a.disabled ? "opacity-40 cursor-not-allowed" : ""}`}>
              {a.label}
            </button>
          );
        })}
      </div>

      {aba === "grupos" && (
        <div>
          <button onClick={() => { setForm({ nome: "", descricao: "" }); setModalTipo("grupo"); setModalOpen(true); }}
            className="btn-primary mb-4">+ Novo Grupo</button>
          <div className="grid sm:grid-cols-2 gap-4">
            {grupos.map(g => (
              <div key={g.id} className="card-hover p-5 flex items-center gap-4"
                onClick={() => carregarGrupo(g.id)}>
                <span className="grid place-items-center w-12 h-12 rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-500 text-white text-lg font-bold shrink-0 shadow-md shadow-indigo-500/25">
                  {g.nome[0]?.toUpperCase()}
                </span>
                <div className="min-w-0 flex-1">
                  <h4 className="font-semibold text-slate-800 truncate">{g.nome}</h4>
                  <p className="text-sm text-slate-400 truncate">{g.descricao || "Sem descrição"}</p>
                </div>
                <span className="text-xs font-medium text-indigo-600 shrink-0">Abrir →</span>
              </div>
            ))}
            {grupos.length === 0 && (
              <div className="card p-10 text-center sm:col-span-2">
                <p className="text-4xl mb-2">👥</p>
                <p className="text-slate-400">Você não participa de nenhum grupo ainda.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {abasDetalhe.includes(aba) && grupoSel && (
        <div>
          <div className="flex flex-wrap gap-1.5 mb-5">
            {["membros", "transacoes", "quemdeve", "orcamento", "mesadas"].map(k => (
              <button key={k} onClick={() => setAba(k)}
                className={`text-sm px-3.5 py-1.5 rounded-xl font-medium transition-all ${aba === k ? "bg-indigo-100 text-indigo-700 shadow-sm" : "text-slate-500 hover:bg-white hover:text-slate-800"}`}>
                {k === "membros" ? "Membros" : k === "transacoes" ? "Transações" : k === "quemdeve" ? "Quem Deve a Quem" : k === "orcamento" ? "Orçamento" : "Mesadas"}
              </button>
            ))}
          </div>

          {aba === "membros" && (
            <div>
              <button onClick={() => { setForm({ usuario_id: "" }); setModalTipo("membro"); setModalOpen(true); }}
                className="btn-primary mb-3">+ Adicionar Membro</button>
              <div className="card overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr><th className="p-3">Nome</th><th className="p-3">Email</th><th className="p-3">Papel</th></tr></thead>
                  <tbody>
                    {membros.map(m => (
                      <tr key={m.id}><td className="p-3 font-medium">{m.nome_usuario}</td><td className="p-3">{m.email_usuario}</td><td className="p-3 capitalize">{m.papel_no_grupo}</td></tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {aba === "transacoes" && (
            <div>
              <button onClick={() => { setForm({ conta: "", categoria: "", valor: "", descricao: "", modo: "igual", divisoes: {} }); setModalTipo("despesa"); setModalOpen(true); }}
                className="btn-primary mb-3">+ Dividir Despesa</button>
              <div className="card overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr><th className="p-3">Descrição</th><th className="p-3">Valor</th><th className="p-3">Data</th></tr></thead>
                  <tbody>
                    {transacoes.map(t => (
                      <tr key={t.id}><td className="p-3">{t.descricao || t.tipo}</td><td className="p-3 text-red-600 font-medium">{formatMoney(t.valor)}</td><td className="p-3">{new Date(t.data).toLocaleDateString("pt-BR")}</td></tr>
                    ))}
                    {transacoes.length === 0 && <tr><td colSpan={3} className="p-3 text-gray-400 text-center">Nenhuma transação</td></tr>}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {aba === "quemdeve" && (
            <div className="card overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr><th className="p-3">Membro</th><th className="p-3">Papel</th><th className="p-3">Saldo</th><th className="p-3">Status</th></tr></thead>
                <tbody>
                  {quemDeve.map(m => (
                    <tr key={m.usuario_id}>
                      <td className="p-3 font-medium">{m.nome}</td>
                      <td className="p-3 capitalize">{m.papel}</td>
                      <td className={`p-3 font-semibold tnum ${m.saldo > 0 ? "text-emerald-600" : m.saldo < 0 ? "text-red-600" : "text-slate-400"}`}>
                        {m.saldo > 0 ? "+" : ""}{formatMoney(m.saldo)}
                      </td>
                      <td className="p-3">
                        {m.status === "a_receber"
                          ? <span className="badge-green">A receber</span>
                          : m.status === "deve"
                            ? <span className="badge-red">Deve</span>
                            : <span className="badge-gray">Quitado</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {aba === "mesadas" && (
            <div>
              <button onClick={() => { setForm({ dependente: "", valor: "", periodo_recarga: "mensal" }); setModalTipo("mesada"); setModalOpen(true); }}
                className="btn-primary mb-3">+ Nova Mesada</button>
              <div className="card overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr><th className="p-3">Dependente</th><th className="p-3">Valor</th><th className="p-3">Recarga</th><th className="p-3">Saldo Atual</th><th className="p-3"></th></tr>
                  </thead>
                  <tbody>
                    {mesadas.map(m => (
                      <tr key={m.id}>
                        <td className="p-3 font-medium">{m.nome_dependente}</td>
                        <td className="p-3">{formatMoney(m.valor)}</td>
                        <td className="p-3 capitalize">{m.periodo_recarga}</td>
                        <td className={`p-3 font-medium ${Number(m.saldo_atual) > 0 ? "text-green-600" : "text-red-600"}`}>{formatMoney(m.saldo_atual)}</td>
                        <td className="p-3">
                          <button onClick={() => recarregarMesada(m)} className="btn-mini-indigo">Recarregar</button>
                        </td>
                      </tr>
                    ))}
                    {mesadas.length === 0 && <tr><td colSpan={5} className="p-3 text-gray-400 text-center">Nenhuma mesada neste grupo.</td></tr>}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {aba === "orcamento" && (
            <div>
              <div className="card overflow-x-auto mb-6">
                <table className="w-full text-sm">
                  <thead><tr><th className="p-3">Categoria</th><th className="p-3">Previsto</th><th className="p-3">Realizado</th><th className="p-3">Diferença</th></tr></thead>
                  <tbody>
                    {orcResumo.map((o, i) => (
                      <tr key={i}>
                        <td className="p-3 font-medium">{o.categoria}</td><td className="p-3">{formatMoney(o.previsto)}</td>
                        <td className="p-3">{formatMoney(o.realizado)}</td>
                        <td className={`p-3 font-medium ${o.diferenca >= 0 ? "text-green-600" : "text-red-600"}`}>{formatMoney(o.diferenca)}</td>
                      </tr>
                    ))}
                    {orcResumo.length === 0 && <tr><td colSpan={4} className="p-3 text-gray-400 text-center">Nenhum orçamento.</td></tr>}
                  </tbody>
                </table>
              </div>
              {orcResumo.length > 0 && (
                <div className="card p-6">
                  <h4 className="font-semibold text-slate-800 mb-1">Previsto × Realizado</h4>
                  <p className="text-xs text-slate-400 mb-4">Orçamento do grupo por categoria.</p>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={orcResumo} barGap={4}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e1e0d9" vertical={false} />
                      <XAxis dataKey="categoria" tick={{ fontSize: 12, fill: "#898781" }} axisLine={{ stroke: "#c3c2b7" }} tickLine={false} />
                      <YAxis tick={{ fontSize: 12, fill: "#898781" }} axisLine={false} tickLine={false} />
                      <Tooltip formatter={(v) => formatMoney(v)} cursor={{ fill: "rgba(42,120,214,0.06)" }}
                        contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0", boxShadow: "0 4px 12px rgba(15,23,42,.08)", fontSize: 13 }} />
                      <Legend iconType="circle" iconSize={9} wrapperStyle={{ fontSize: 13, color: "#52514e" }} />
                      <Bar dataKey="previsto" fill="#2a78d6" name="Previsto" radius={[4, 4, 0, 0]} maxBarSize={36} />
                      <Bar dataKey="realizado" fill="#1baf7a" name="Realizado" radius={[4, 4, 0, 0]} maxBarSize={36} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Modals */}
      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title={modalTipo === "grupo" ? "Novo Grupo" : modalTipo === "membro" ? "Adicionar Membro" : modalTipo === "mesada" ? "Nova Mesada" : "Dividir Despesa"}>
        {modalTipo === "mesada" && (
          <div className="space-y-3">
            <select className="input" value={form.dependente || ""} onChange={e => setForm({ ...form, dependente: e.target.value })}>
              <option value="">Dependente</option>
              {membros.filter(m => m.papel_no_grupo === "dependente").map(m => (
                <option key={m.usuario} value={m.usuario}>{m.nome_usuario}</option>
              ))}
            </select>
            <input className="input" type="number" step="0.01" placeholder="Valor da mesada" value={form.valor || ""} onChange={e => setForm({ ...form, valor: e.target.value })} />
            <select className="input" value={form.periodo_recarga || "mensal"} onChange={e => setForm({ ...form, periodo_recarga: e.target.value })}>
              <option value="semanal">Semanal</option>
              <option value="quinzenal">Quinzenal</option>
              <option value="mensal">Mensal</option>
            </select>
            <button onClick={criarMesada} className="btn-primary w-full">Criar Mesada</button>
          </div>
        )}
        {modalTipo === "grupo" && (
          <div className="space-y-3">
            <input className="input" placeholder="Nome do grupo" value={form.nome || ""} onChange={e => setForm({ ...form, nome: e.target.value })} />
            <input className="input" placeholder="Descrição" value={form.descricao || ""} onChange={e => setForm({ ...form, descricao: e.target.value })} />
            <button onClick={criarGrupo} className="btn-primary w-full">Criar</button>
          </div>
        )}
        {modalTipo === "membro" && (
          <div className="space-y-3">
            <input className="input" type="number" placeholder="ID do usuário" value={form.usuario_id || ""} onChange={e => setForm({ ...form, usuario_id: e.target.value })} />
            <button onClick={adicionarMembro} className="btn-primary w-full">Adicionar</button>
          </div>
        )}
        {modalTipo === "despesa" && (
          <div className="space-y-3">
            <select className="input" value={form.conta || ""} onChange={e => setForm({ ...form, conta: e.target.value })}>
              <option value="">Conta</option>
              {contas.map(c => <option key={c.id} value={c.id}>{c.nome}</option>)}
            </select>
            <select className="input" value={form.categoria || ""} onChange={e => setForm({ ...form, categoria: e.target.value })}>
              <option value="">Categoria</option>
              {categorias.map(c => <option key={c.id} value={c.id}>{c.nome}</option>)}
            </select>
            <input className="input" type="number" step="0.01" placeholder="Valor" value={form.valor || ""} onChange={e => setForm({ ...form, valor: e.target.value })} />
            <input className="input" placeholder="Descrição" value={form.descricao || ""} onChange={e => setForm({ ...form, descricao: e.target.value })} />
            <div className="flex gap-2">
              <button onClick={() => setForm({ ...form, modo: "igual" })} className={`flex-1 py-1.5 text-sm rounded ${form.modo === "igual" ? "bg-indigo-600 text-white" : "bg-gray-200"}`}>Partes Iguais</button>
              <button onClick={() => setForm({ ...form, modo: "manual" })} className={`flex-1 py-1.5 text-sm rounded ${form.modo === "manual" ? "bg-indigo-600 text-white" : "bg-gray-200"}`}>Manual</button>
            </div>
            {form.modo === "manual" && (
              <div className="space-y-2 bg-slate-50 rounded-xl p-3">
                <p className="text-xs text-slate-500 font-medium">Quanto cada um deve? A soma precisa fechar com o valor total.</p>
                {membrosDivisao.map(m => (
                  <div key={m.usuario} className="flex items-center gap-2">
                    <span className="text-sm text-slate-600 flex-1 truncate">{m.nome_usuario}</span>
                    <input type="number" step="0.01" min="0" className="input w-28 py-1.5" placeholder="0,00"
                      value={form.divisoes?.[m.usuario] || ""}
                      onChange={e => setForm({ ...form, divisoes: { ...form.divisoes, [m.usuario]: e.target.value } })} />
                  </div>
                ))}
                <p className="text-xs text-slate-400 text-right tnum">
                  Soma: {Object.values(form.divisoes || {}).reduce((s, v) => s + (Number(v) || 0), 0).toFixed(2)}
                  {form.valor ? ` / ${Number(form.valor).toFixed(2)}` : ""}
                </p>
              </div>
            )}
            <button onClick={dividirDespesa} className="btn-primary w-full">Registrar e Dividir</button>
          </div>
        )}
      </Modal>
    </div>
  );
}
