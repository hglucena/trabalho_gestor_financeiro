import { useState, useEffect, useCallback } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import api from "../api/client";
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
        api.get("/transacoes/"),
        api.get("/mesadas/"),
      ]);
      const tGrupo = (t.data.results || []).filter(tx => tx.grupo === gid);
      setMembros(mr.data.results || []);
      setTransacoes(tGrupo);
      setMesadas((ms.data.results || []).filter(m => m.grupo === gid));
      const q = await api.get(`/grupos/${gid}/quem_deve_a_quem/`);
      setQuemDeve(q.data.membros || []);
      const o = await api.get(`/grupos/${gid}/orcamento_resumo/`);
      setOrcResumo(o.data.orcamentos || []);
    } catch { }
  };

  const extrairErro = (e, fallback) => {
    const data = e.response?.data;
    if (typeof data?.detail === "string") return data.detail;
    if (data && typeof data === "object") return JSON.stringify(data);
    return fallback;
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
        data.participantes_ids = membros.map(m => m.usuario);
      } else {
        data.divisoes = form.divisoes || [];
      }
      await api.post("/transacoes/", data);
      setModalOpen(false);
      carregarGrupo(grupoSel);
      setMsg("Despesa dividida com sucesso!");
    } catch (e) {
      setMsg(e.response?.data ? JSON.stringify(e.response.data) : "Erro na divisão.");
    }
  };

  const abas = [
    { key: "grupos", label: "Meus Grupos" },
    { key: "detalhe", label: "Detalhes do Grupo", disabled: !grupoSel },
  ];
  const abasDetalhe = ["detalhe", "membros", "transacoes", "quemdeve", "orcamento", "mesadas"];

  return (
    <div>
      <h2 className="text-xl font-bold mb-2">Painel do Gestor — {user?.nome}</h2>
      {msg && (
        <div className={`p-2 rounded text-sm mb-3 ${msg.startsWith("Erro") ? "bg-red-100 text-red-800" : "bg-green-100 text-green-800"}`}>
          {msg}
          <button onClick={() => setMsg("")} className="float-right font-bold px-1">×</button>
        </div>
      )}

      <div className="flex flex-wrap gap-2 mb-4 border-b">
        {abas.map(a => {
          const ativa = a.key === "grupos" ? aba === "grupos" : abasDetalhe.includes(aba);
          return (
            <button key={a.key} onClick={() => a.key === "grupos" ? setAba("grupos") : grupoSel && setAba("membros")}
              className={`px-4 py-2 text-sm font-medium rounded-t-lg ${ativa ? "bg-white border border-b-white -mb-px text-indigo-600" : "text-gray-500 hover:text-gray-700"} ${a.disabled ? "opacity-40 cursor-not-allowed" : ""}`}>
              {a.label}
            </button>
          );
        })}
      </div>

      {aba === "grupos" && (
        <div>
          <button onClick={() => { setForm({ nome: "", descricao: "" }); setModalTipo("grupo"); setModalOpen(true); }}
            className="bg-indigo-600 text-white px-3 py-1.5 rounded text-sm hover:bg-indigo-700 mb-3">+ Novo Grupo</button>
          <div className="grid gap-3">
            {grupos.map(g => (
              <div key={g.id} className="bg-white rounded-lg shadow p-4 flex justify-between items-center cursor-pointer hover:shadow-md"
                onClick={() => carregarGrupo(g.id)}>
                <div>
                  <h4 className="font-semibold">{g.nome}</h4>
                  <p className="text-sm text-gray-500">{g.descricao}</p>
                </div>
                <span className="text-xs text-indigo-600">Ver detalhes →</span>
              </div>
            ))}
            {grupos.length === 0 && <p className="text-gray-400">Você não participa de nenhum grupo.</p>}
          </div>
        </div>
      )}

      {abasDetalhe.includes(aba) && grupoSel && (
        <div>
          <div className="flex flex-wrap gap-3 mb-4 border-b pb-2">
            {["membros", "transacoes", "quemdeve", "orcamento", "mesadas"].map(k => (
              <button key={k} onClick={() => setAba(k)}
                className={`text-sm px-3 py-1 rounded ${aba === k ? "bg-indigo-100 text-indigo-700 font-medium" : "text-gray-500"}`}>
                {k === "membros" ? "Membros" : k === "transacoes" ? "Transações" : k === "quemdeve" ? "Quem Deve a Quem" : k === "orcamento" ? "Orçamento" : "Mesadas"}
              </button>
            ))}
          </div>

          {aba === "membros" && (
            <div>
              <button onClick={() => { setForm({ usuario_id: "" }); setModalTipo("membro"); setModalOpen(true); }}
                className="bg-indigo-600 text-white px-3 py-1.5 rounded text-sm hover:bg-indigo-700 mb-3">+ Adicionar Membro</button>
              <div className="bg-white rounded-lg shadow overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50"><tr><th className="p-3">Nome</th><th className="p-3">Email</th><th className="p-3">Papel</th></tr></thead>
                  <tbody>
                    {membros.map(m => (
                      <tr key={m.id} className="border-t"><td className="p-3 font-medium">{m.nome_usuario}</td><td className="p-3">{m.email_usuario}</td><td className="p-3 capitalize">{m.papel_no_grupo}</td></tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {aba === "transacoes" && (
            <div>
              <button onClick={() => { setForm({ conta: "", categoria: "", valor: "", descricao: "", modo: "igual", divisoes: [] }); setModalTipo("despesa"); setModalOpen(true); }}
                className="bg-indigo-600 text-white px-3 py-1.5 rounded text-sm hover:bg-indigo-700 mb-3">+ Dividir Despesa</button>
              <div className="bg-white rounded-lg shadow overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50"><tr><th className="p-3">Descrição</th><th className="p-3">Valor</th><th className="p-3">Data</th></tr></thead>
                  <tbody>
                    {transacoes.map(t => (
                      <tr key={t.id} className="border-t"><td className="p-3">{t.descricao || t.tipo}</td><td className="p-3 text-red-600 font-medium">{formatMoney(t.valor)}</td><td className="p-3">{new Date(t.data).toLocaleDateString("pt-BR")}</td></tr>
                    ))}
                    {transacoes.length === 0 && <tr><td colSpan={3} className="p-3 text-gray-400 text-center">Nenhuma transação</td></tr>}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {aba === "quemdeve" && (
            <div className="bg-white rounded-lg shadow overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50"><tr><th className="p-3">Membro</th><th className="p-3">Papel</th><th className="p-3">Saldo</th><th className="p-3">Status</th></tr></thead>
                <tbody>
                  {quemDeve.map(m => (
                    <tr key={m.usuario_id} className="border-t">
                      <td className="p-3 font-medium">{m.nome}</td>
                      <td className="p-3 capitalize">{m.papel}</td>
                      <td className={`p-3 font-medium ${m.saldo > 0 ? "text-green-600" : m.saldo < 0 ? "text-red-600" : "text-gray-500"}`}>
                        {m.saldo > 0 ? "+" : ""}{formatMoney(m.saldo)}
                      </td>
                      <td className="p-3 capitalize">{m.status.replace("_", " ")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {aba === "mesadas" && (
            <div>
              <button onClick={() => { setForm({ dependente: "", valor: "", periodo_recarga: "mensal" }); setModalTipo("mesada"); setModalOpen(true); }}
                className="bg-indigo-600 text-white px-3 py-1.5 rounded text-sm hover:bg-indigo-700 mb-3">+ Nova Mesada</button>
              <div className="bg-white rounded-lg shadow overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 text-left">
                    <tr><th className="p-3">Dependente</th><th className="p-3">Valor</th><th className="p-3">Recarga</th><th className="p-3">Saldo Atual</th><th className="p-3"></th></tr>
                  </thead>
                  <tbody>
                    {mesadas.map(m => (
                      <tr key={m.id} className="border-t">
                        <td className="p-3 font-medium">{m.nome_dependente}</td>
                        <td className="p-3">{formatMoney(m.valor)}</td>
                        <td className="p-3 capitalize">{m.periodo_recarga}</td>
                        <td className={`p-3 font-medium ${Number(m.saldo_atual) > 0 ? "text-green-600" : "text-red-600"}`}>{formatMoney(m.saldo_atual)}</td>
                        <td className="p-3">
                          <button onClick={() => recarregarMesada(m)} className="text-indigo-600 hover:underline text-xs">Recarregar</button>
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
              <div className="bg-white rounded-lg shadow overflow-x-auto mb-6">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50"><tr><th className="p-3">Categoria</th><th className="p-3">Previsto</th><th className="p-3">Realizado</th><th className="p-3">Diferença</th></tr></thead>
                  <tbody>
                    {orcResumo.map((o, i) => (
                      <tr key={i} className="border-t">
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
                <div className="bg-white rounded-lg shadow p-4">
                  <h4 className="font-semibold mb-3">Previsto × Realizado</h4>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={orcResumo}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="categoria" />
                      <YAxis />
                      <Tooltip formatter={(v) => formatMoney(v)} />
                      <Bar dataKey="previsto" fill="#6366f1" name="Previsto" />
                      <Bar dataKey="realizado" fill="#ef4444" name="Realizado" />
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
            <select className="w-full border rounded px-3 py-2 text-sm" value={form.dependente || ""} onChange={e => setForm({ ...form, dependente: e.target.value })}>
              <option value="">Dependente</option>
              {membros.filter(m => m.papel_no_grupo === "dependente").map(m => (
                <option key={m.usuario} value={m.usuario}>{m.nome_usuario}</option>
              ))}
            </select>
            <input className="w-full border rounded px-3 py-2 text-sm" type="number" step="0.01" placeholder="Valor da mesada" value={form.valor || ""} onChange={e => setForm({ ...form, valor: e.target.value })} />
            <select className="w-full border rounded px-3 py-2 text-sm" value={form.periodo_recarga || "mensal"} onChange={e => setForm({ ...form, periodo_recarga: e.target.value })}>
              <option value="semanal">Semanal</option>
              <option value="quinzenal">Quinzenal</option>
              <option value="mensal">Mensal</option>
            </select>
            <button onClick={criarMesada} className="w-full bg-indigo-600 text-white rounded-lg py-2 text-sm hover:bg-indigo-700">Criar Mesada</button>
          </div>
        )}
        {modalTipo === "grupo" && (
          <div className="space-y-3">
            <input className="w-full border rounded px-3 py-2 text-sm" placeholder="Nome do grupo" value={form.nome || ""} onChange={e => setForm({ ...form, nome: e.target.value })} />
            <input className="w-full border rounded px-3 py-2 text-sm" placeholder="Descrição" value={form.descricao || ""} onChange={e => setForm({ ...form, descricao: e.target.value })} />
            <button onClick={criarGrupo} className="w-full bg-indigo-600 text-white rounded-lg py-2 text-sm hover:bg-indigo-700">Criar</button>
          </div>
        )}
        {modalTipo === "membro" && (
          <div className="space-y-3">
            <input className="w-full border rounded px-3 py-2 text-sm" type="number" placeholder="ID do usuário" value={form.usuario_id || ""} onChange={e => setForm({ ...form, usuario_id: e.target.value })} />
            <button onClick={adicionarMembro} className="w-full bg-indigo-600 text-white rounded-lg py-2 text-sm hover:bg-indigo-700">Adicionar</button>
          </div>
        )}
        {modalTipo === "despesa" && (
          <div className="space-y-3">
            <select className="w-full border rounded px-3 py-2 text-sm" value={form.conta || ""} onChange={e => setForm({ ...form, conta: e.target.value })}>
              <option value="">Conta</option>
              {contas.map(c => <option key={c.id} value={c.id}>{c.nome}</option>)}
            </select>
            <select className="w-full border rounded px-3 py-2 text-sm" value={form.categoria || ""} onChange={e => setForm({ ...form, categoria: e.target.value })}>
              <option value="">Categoria</option>
              {categorias.map(c => <option key={c.id} value={c.id}>{c.nome}</option>)}
            </select>
            <input className="w-full border rounded px-3 py-2 text-sm" type="number" step="0.01" placeholder="Valor" value={form.valor || ""} onChange={e => setForm({ ...form, valor: e.target.value })} />
            <input className="w-full border rounded px-3 py-2 text-sm" placeholder="Descrição" value={form.descricao || ""} onChange={e => setForm({ ...form, descricao: e.target.value })} />
            <div className="flex gap-2">
              <button onClick={() => setForm({ ...form, modo: "igual" })} className={`flex-1 py-1.5 text-sm rounded ${form.modo === "igual" ? "bg-indigo-600 text-white" : "bg-gray-200"}`}>Partes Iguais</button>
              <button onClick={() => setForm({ ...form, modo: "manual" })} className={`flex-1 py-1.5 text-sm rounded ${form.modo === "manual" ? "bg-indigo-600 text-white" : "bg-gray-200"}`}>Manual</button>
            </div>
            {form.modo === "manual" && (
              <div className="text-xs text-gray-500">Edite os valores diretamente na API ou use partes iguais.</div>
            )}
            <button onClick={dividirDespesa} className="w-full bg-indigo-600 text-white rounded-lg py-2 text-sm hover:bg-indigo-700">Registrar e Dividir</button>
          </div>
        )}
      </Modal>
    </div>
  );
}
