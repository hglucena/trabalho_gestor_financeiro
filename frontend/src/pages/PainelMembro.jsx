import { useState, useEffect, useCallback, useRef } from "react";
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from "recharts";
import api from "../api/client";
import { useAuth } from "../contexts/AuthContext";
import Modal from "../components/Modal";

const COLORS = ["#6366f1", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4", "#ec4899"];

function formatMoney(v) {
  return Number(v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function extrairErro(err, fallback) {
  const data = err.response?.data;
  if (!data) return fallback;
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.non_field_errors)) return data.non_field_errors.join(" ");
  if (typeof data === "object") {
    const partes = Object.entries(data).map(([campo, erros]) =>
      `${campo}: ${Array.isArray(erros) ? erros.join(" ") : erros}`);
    if (partes.length) return partes.join(" | ");
  }
  return fallback;
}

export default function PainelMembro() {
  const { user } = useAuth();
  const [aba, setAba] = useState("contas");
  const [contas, setContas] = useState([]);
  const [transacoes, setTransacoes] = useState([]);
  const [categorias, setCategorias] = useState([]);
  const [orcamentos, setOrcamentos] = useState([]);
  const [contasAPagar, setContasAPagar] = useState([]);
  const [metas, setMetas] = useState([]);
  const [autorizacoes, setAutorizacoes] = useState([]);
  const [recomendacoes, setRecomendacoes] = useState([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editando, setEditando] = useState(null);
  const [form, setForm] = useState({});
  const [msg, setMsg] = useState(null); // { tipo: "ok" | "erro", texto }
  const csvInputRef = useRef(null);

  const load = useCallback(async (url, setter) => {
    try {
      const res = await api.get(url);
      setter(res.data.results || [res.data]);
    } catch { }
  }, []);

  useEffect(() => { load("/contas/", setContas); }, [load]);
  useEffect(() => { load("/transacoes/", setTransacoes); }, [load]);
  useEffect(() => { load("/categorias/", setCategorias); }, [load]);
  useEffect(() => { load("/orcamentos/", setOrcamentos); }, [load]);
  useEffect(() => { load("/contas-a-pagar/", setContasAPagar); }, [load]);
  useEffect(() => { load("/metas/", setMetas); }, [load]);
  useEffect(() => { load("/autorizacoes/", setAutorizacoes); }, [load]);
  useEffect(() => { load("/recomendacoes/", setRecomendacoes); }, [load]);

  const setters = {
    "/contas/": setContas,
    "/transacoes/": setTransacoes,
    "/categorias/": setCategorias,
    "/orcamentos/": setOrcamentos,
    "/contas-a-pagar/": setContasAPagar,
    "/metas/": setMetas,
    "/autorizacoes/": setAutorizacoes,
  };

  const salvar = async (endpoint, dados) => {
    setMsg(null);
    try {
      if (editando) {
        await api.patch(`${endpoint}${editando.id}/`, dados);
      } else {
        await api.post(endpoint, dados);
      }
      setModalOpen(false);
      setEditando(null);
      load(endpoint, setters[endpoint]);
      if (endpoint === "/transacoes/") load("/contas/", setContas); // saldo vivo
    } catch (err) {
      setMsg({ tipo: "erro", texto: extrairErro(err, "Erro ao salvar.") });
    }
  };

  const deletar = async (endpoint, id, setter) => {
    if (!confirm("Confirmar exclusão?")) return;
    try {
      await api.delete(`${endpoint}${id}/`);
      load(endpoint, setter);
    } catch (err) {
      setMsg({ tipo: "erro", texto: extrairErro(err, "Erro ao excluir.") });
    }
  };

  const abrirModal = (dados = {}) => {
    setEditando(dados.id ? dados : null);
    setForm(dados.id ? { ...dados } : { nome: "", saldo_inicial: "0", tipo: "despesa", valor: "", descricao: "", conta: "", categoria: "", vencimento: "", valor_alvo: "", prazo: "", consultor_email: "", nivel: "leitura" });
    setModalOpen(true);
  };

  const importarCSV = async (arquivo) => {
    setMsg(null);
    if (!arquivo) return;
    if (!contas.length) {
      setMsg({ tipo: "erro", texto: "Crie uma conta antes de importar o extrato." });
      return;
    }
    const dados = new FormData();
    dados.append("arquivo", arquivo);
    dados.append("conta", contas[0].id);
    try {
      const r = await api.post("/transacoes/importar_csv/", dados, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      const { importadas, erros } = r.data;
      setMsg({
        tipo: erros.length ? "erro" : "ok",
        texto: `${importadas} transação(ões) importada(s) para a conta "${contas[0].nome}".` +
          (erros.length ? ` ${erros.length} linha(s) com erro: ${erros.map(e => `linha ${e.linha} (${e.erro})`).join("; ")}` : ""),
      });
      load("/transacoes/", setTransacoes);
      load("/categorias/", setCategorias);
    } catch (err) {
      setMsg({ tipo: "erro", texto: extrairErro(err, "Erro ao importar o CSV.") });
    }
  };

  const aportar = async (meta) => {
    const valor = prompt(`Quanto você quer guardar na meta "${meta.nome}"?`);
    if (!valor) return;
    setMsg(null);
    try {
      await api.post(`/metas/${meta.id}/aportar/`, { valor });
      load("/metas/", setMetas);
      load("/contas/", setContas);
      load("/transacoes/", setTransacoes);
    } catch (err) {
      setMsg({ tipo: "erro", texto: extrairErro(err, "Erro no aporte.") });
    }
  };

  const revogarAutorizacao = async (autorizacao) => {
    if (!confirm(`Revogar o acesso de ${autorizacao.nome_consultor}?`)) return;
    try {
      await api.patch(`/autorizacoes/${autorizacao.id}/`, { status: false });
      load("/autorizacoes/", setAutorizacoes);
    } catch (err) {
      setMsg({ tipo: "erro", texto: extrairErro(err, "Erro ao revogar.") });
    }
  };

  const reativarAutorizacao = async (autorizacao) => {
    try {
      await api.patch(`/autorizacoes/${autorizacao.id}/`, { status: true });
      load("/autorizacoes/", setAutorizacoes);
    } catch (err) {
      setMsg({ tipo: "erro", texto: extrairErro(err, "Erro ao reativar.") });
    }
  };

  const abas = [
    { key: "contas", label: "Contas" },
    { key: "transacoes", label: "Transações" },
    { key: "categorias", label: "Categorias" },
    { key: "apagar", label: "A Pagar" },
    { key: "metas", label: "Metas" },
    { key: "consultores", label: "Consultores" },
    { key: "grafico", label: "Gráfico" },
  ];

  // Dados para gráfico
  const despesasPorCat = transacoes
    .filter(t => t.tipo === "despesa")
    .reduce((acc, t) => {
      const nome = t.nome_categoria || "Sem categoria";
      acc[nome] = (acc[nome] || 0) + Number(t.valor);
      return acc;
    }, {});
  const graficoData = Object.entries(despesasPorCat).map(([name, value]) => ({ name, value }));

  const saldoTotal = contas.reduce((s, c) => s + Number(c.saldo_atual ?? c.saldo_inicial ?? 0), 0);

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">Painel de {user?.nome}</h2>
      <p className="text-sm text-gray-500 mb-4">Saldo total: <span className={`font-bold ${saldoTotal < 0 ? "text-red-600" : "text-green-600"}`}>{formatMoney(saldoTotal)}</span></p>

      {msg && (
        <div className={`p-2 rounded text-sm mb-3 ${msg.tipo === "erro" ? "bg-red-100 text-red-800" : "bg-green-100 text-green-800"}`}>
          {msg.texto}
          <button onClick={() => setMsg(null)} className="float-right font-bold px-1">×</button>
        </div>
      )}

      <div className="flex flex-wrap gap-2 mb-6 border-b">
        {abas.map(a => (
          <button key={a.key} onClick={() => setAba(a.key)}
            className={`px-4 py-2 text-sm font-medium rounded-t-lg ${aba === a.key ? "bg-white border border-b-white -mb-px text-indigo-600" : "text-gray-500 hover:text-gray-700"}`}>
            {a.label}
          </button>
        ))}
      </div>

      {/* Contas */}
      {aba === "contas" && (
        <div>
          <div className="flex justify-between items-center mb-3">
            <h3 className="font-semibold">Minhas Contas</h3>
            <button onClick={() => abrirModal()} className="bg-indigo-600 text-white px-3 py-1.5 rounded text-sm hover:bg-indigo-700">
              + Nova Conta
            </button>
          </div>
          <div className="bg-white rounded-lg shadow overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-left">
                <tr><th className="p-3">Nome</th><th className="p-3">Saldo Inicial</th><th className="p-3">Saldo Atual</th><th className="p-3">Ativa</th><th className="p-3"></th></tr>
              </thead>
              <tbody>
                {contas.map(c => (
                  <tr key={c.id} className="border-t hover:bg-gray-50">
                    <td className="p-3 font-medium">{c.nome}</td>
                    <td className="p-3">{formatMoney(c.saldo_inicial)}</td>
                    <td className={`p-3 font-medium ${Number(c.saldo_atual) < 0 ? "text-red-600" : "text-green-600"}`}>{formatMoney(c.saldo_atual)}</td>
                    <td className="p-3">{c.ativa ? "Sim" : "Não"}</td>
                    <td className="p-3 flex gap-2">
                      <button onClick={() => abrirModal(c)} className="text-indigo-600 hover:underline text-xs">Editar</button>
                      <button onClick={() => deletar("/contas/", c.id, setContas)} className="text-red-600 hover:underline text-xs">Excluir</button>
                    </td>
                  </tr>
                ))}
                {contas.length === 0 && <tr><td colSpan={4} className="p-3 text-gray-400 text-center">Nenhuma conta</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Transações */}
      {aba === "transacoes" && (
        <div>
          <div className="flex flex-wrap justify-between items-center gap-2 mb-3">
            <h3 className="font-semibold">Transações</h3>
            <div className="flex gap-2">
              <input ref={csvInputRef} type="file" accept=".csv" className="hidden"
                onChange={e => { importarCSV(e.target.files[0]); e.target.value = ""; }} />
              <button onClick={() => csvInputRef.current?.click()}
                className="bg-gray-200 text-gray-700 px-3 py-1.5 rounded text-sm hover:bg-gray-300"
                title="CSV com colunas: data,descricao,valor,tipo,categoria">
                Importar CSV
              </button>
              <button onClick={() => abrirModal()} className="bg-indigo-600 text-white px-3 py-1.5 rounded text-sm hover:bg-indigo-700">
                + Nova Transação
              </button>
            </div>
          </div>
          <div className="bg-white rounded-lg shadow overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-left">
                <tr><th className="p-3">Descrição</th><th className="p-3">Valor</th><th className="p-3">Conta</th><th className="p-3">Categoria</th><th className="p-3">Data</th><th className="p-3"></th></tr>
              </thead>
              <tbody>
                {transacoes.map(t => (
                  <tr key={t.id} className="border-t hover:bg-gray-50">
                    <td className="p-3 font-medium">{t.descricao || t.tipo}</td>
                    <td className={`p-3 font-medium ${t.tipo === "receita" ? "text-green-600" : "text-red-600"}`}>
                      {t.tipo === "receita" ? "+" : "-"}{formatMoney(t.valor)}
                    </td>
                    <td className="p-3">{t.nome_conta}</td>
                    <td className="p-3">{t.nome_categoria}</td>
                    <td className="p-3">{new Date(t.data).toLocaleDateString("pt-BR")}</td>
                    <td className="p-3 flex gap-2">
                      <button onClick={() => abrirModal(t)} className="text-indigo-600 hover:underline text-xs">Editar</button>
                      <button onClick={() => deletar("/transacoes/", t.id, setTransacoes)} className="text-red-600 hover:underline text-xs">Excluir</button>
                    </td>
                  </tr>
                ))}
                {transacoes.length === 0 && <tr><td colSpan={6} className="p-3 text-gray-400 text-center">Nenhuma transação</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Categorias */}
      {aba === "categorias" && (
        <div>
          <div className="flex justify-between items-center mb-3">
            <h3 className="font-semibold">Categorias</h3>
            <button onClick={() => abrirModal()} className="bg-indigo-600 text-white px-3 py-1.5 rounded text-sm hover:bg-indigo-700">
              + Nova Categoria
            </button>
          </div>
          <div className="bg-white rounded-lg shadow overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-left">
                <tr><th className="p-3">Nome</th><th className="p-3">Tipo</th><th className="p-3">Padrão</th><th className="p-3"></th></tr>
              </thead>
              <tbody>
                {categorias.map(c => (
                  <tr key={c.id} className="border-t hover:bg-gray-50">
                    <td className="p-3 font-medium">{c.nome}</td>
                    <td className="p-3 capitalize">{c.tipo}</td>
                    <td className="p-3">{c.padrao ? "Sim" : "Não"}</td>
                    <td className="p-3 flex gap-2">
                      {!c.padrao && (
                        <>
                          <button onClick={() => abrirModal(c)} className="text-indigo-600 hover:underline text-xs">Editar</button>
                          <button onClick={() => deletar("/categorias/", c.id, setCategorias)} className="text-red-600 hover:underline text-xs">Excluir</button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
                {categorias.length === 0 && <tr><td colSpan={4} className="p-3 text-gray-400 text-center">Nenhuma categoria</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Contas a Pagar */}
      {aba === "apagar" && (
        <div>
          <div className="flex justify-between items-center mb-3">
            <h3 className="font-semibold">Contas a Pagar</h3>
            <button onClick={() => abrirModal()} className="bg-indigo-600 text-white px-3 py-1.5 rounded text-sm hover:bg-indigo-700">
              + Nova Conta a Pagar
            </button>
          </div>
          <div className="bg-white rounded-lg shadow overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-left">
                <tr><th className="p-3">Descrição</th><th className="p-3">Valor</th><th className="p-3">Vencimento</th><th className="p-3">Status</th><th className="p-3"></th></tr>
              </thead>
              <tbody>
                {contasAPagar.map(c => {
                  const vencida = !c.pago && new Date(c.vencimento + "T23:59:59") < new Date();
                  return (
                    <tr key={c.id} className="border-t hover:bg-gray-50">
                      <td className="p-3 font-medium">{c.descricao}{c.recorrencia ? " 🔁" : ""}</td>
                      <td className="p-3">{formatMoney(c.valor)}</td>
                      <td className="p-3">{new Date(c.vencimento + "T12:00:00").toLocaleDateString("pt-BR")}</td>
                      <td className="p-3">
                        {c.pago
                          ? <span className="text-green-600 font-medium">Paga</span>
                          : vencida
                            ? <span className="text-red-600 font-medium">Vencida</span>
                            : <span className="text-amber-600 font-medium">Em aberto</span>}
                      </td>
                      <td className="p-3 flex gap-2">
                        {!c.pago && (
                          <button onClick={async () => {
                            setMsg(null);
                            try {
                              await api.post(`/contas-a-pagar/${c.id}/pagar/`);
                              load("/contas-a-pagar/", setContasAPagar);
                              load("/contas/", setContas);
                              load("/transacoes/", setTransacoes);
                              setMsg({ tipo: "ok", texto: `"${c.descricao}" paga — despesa lançada e saldo atualizado.` });
                            } catch (err) {
                              setMsg({ tipo: "erro", texto: extrairErro(err, "Erro ao pagar.") });
                            }
                          }} className="text-green-600 hover:underline text-xs">Marcar paga</button>
                        )}
                        <button onClick={() => abrirModal(c)} className="text-indigo-600 hover:underline text-xs">Editar</button>
                        <button onClick={() => deletar("/contas-a-pagar/", c.id, setContasAPagar)} className="text-red-600 hover:underline text-xs">Excluir</button>
                      </td>
                    </tr>
                  );
                })}
                {contasAPagar.length === 0 && <tr><td colSpan={5} className="p-3 text-gray-400 text-center">Nenhuma conta a pagar</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Metas de economia */}
      {aba === "metas" && (
        <div>
          <div className="flex justify-between items-center mb-3">
            <h3 className="font-semibold">Metas de Economia</h3>
            <button onClick={() => abrirModal()} className="bg-indigo-600 text-white px-3 py-1.5 rounded text-sm hover:bg-indigo-700">
              + Nova Meta
            </button>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            {metas.map(m => (
              <div key={m.id} className="bg-white rounded-lg shadow p-4">
                <div className="flex justify-between items-start mb-2">
                  <h4 className="font-semibold">{m.nome} {m.concluida && <span className="text-green-600 text-xs ml-1">✓ concluída</span>}</h4>
                  <button onClick={() => deletar("/metas/", m.id, setMetas)} className="text-red-600 hover:underline text-xs">Excluir</button>
                </div>
                <p className="text-sm text-gray-500 mb-2">
                  {formatMoney(m.valor_atual)} de {formatMoney(m.valor_alvo)}
                  {m.prazo && ` — até ${new Date(m.prazo + "T12:00:00").toLocaleDateString("pt-BR")}`}
                </p>
                <div className="w-full bg-gray-200 rounded-full h-2.5 mb-3">
                  <div className={`h-2.5 rounded-full ${m.concluida ? "bg-green-500" : "bg-indigo-600"}`} style={{ width: `${m.percentual}%` }} />
                </div>
                <button onClick={() => aportar(m)} className="bg-indigo-600 text-white px-3 py-1 rounded text-xs hover:bg-indigo-700">
                  + Guardar dinheiro
                </button>
              </div>
            ))}
            {metas.length === 0 && <p className="text-gray-400">Nenhuma meta criada. Crie uma para começar a poupar!</p>}
          </div>
        </div>
      )}

      {/* Consultores */}
      {aba === "consultores" && (
        <div className="space-y-6">
          <div>
            <div className="flex justify-between items-center mb-3">
              <h3 className="font-semibold">Meus Consultores</h3>
              <button onClick={() => abrirModal()} className="bg-indigo-600 text-white px-3 py-1.5 rounded text-sm hover:bg-indigo-700">
                + Autorizar Consultor
              </button>
            </div>
            <div className="bg-white rounded-lg shadow overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 text-left">
                  <tr><th className="p-3">Consultor</th><th className="p-3">E-mail</th><th className="p-3">Nível</th><th className="p-3">Status</th><th className="p-3"></th></tr>
                </thead>
                <tbody>
                  {autorizacoes.filter(a => a.cliente === user?.id).map(a => (
                    <tr key={a.id} className="border-t hover:bg-gray-50">
                      <td className="p-3 font-medium">{a.nome_consultor}</td>
                      <td className="p-3">{a.email_consultor}</td>
                      <td className="p-3 capitalize">{a.nivel}</td>
                      <td className="p-3">
                        {a.status
                          ? <span className="text-green-600 font-medium">Ativa</span>
                          : <span className="text-gray-400">Revogada</span>}
                      </td>
                      <td className="p-3">
                        {a.status
                          ? <button onClick={() => revogarAutorizacao(a)} className="text-red-600 hover:underline text-xs">Revogar</button>
                          : <button onClick={() => reativarAutorizacao(a)} className="text-green-600 hover:underline text-xs">Reativar</button>}
                      </td>
                    </tr>
                  ))}
                  {autorizacoes.filter(a => a.cliente === user?.id).length === 0 && (
                    <tr><td colSpan={5} className="p-3 text-gray-400 text-center">Você ainda não autorizou nenhum consultor.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div>
            <h3 className="font-semibold mb-3">Recomendações recebidas</h3>
            <div className="space-y-3">
              {recomendacoes.filter(r => r.cliente === user?.id).map(r => (
                <div key={r.id} className="bg-white rounded-lg shadow p-4">
                  <p className="text-sm">{r.texto}</p>
                  <p className="text-xs text-gray-400 mt-2">
                    {r.nome_consultor} — {new Date(r.data).toLocaleDateString("pt-BR")}
                  </p>
                </div>
              ))}
              {recomendacoes.filter(r => r.cliente === user?.id).length === 0 && (
                <p className="text-gray-400 text-sm">Nenhuma recomendação recebida.</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Gráfico */}
      {aba === "grafico" && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="font-semibold mb-4">Despesas por Categoria</h3>
          {graficoData.length > 0 ? (
            <ResponsiveContainer width="100%" height={350}>
              <PieChart>
                <Pie data={graficoData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={120} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                  {graficoData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip formatter={(v) => formatMoney(v)} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-gray-400 text-center py-10">Nenhuma despesa registrada.</p>
          )}
        </div>
      )}

      {/* Modal CRUD */}
      <Modal isOpen={modalOpen} onClose={() => { setModalOpen(false); setEditando(null); }}
        title={editando ? `Editar ${editando.nome || editando.descricao || ""}` : "Novo"}>
        <form onSubmit={(e) => { e.preventDefault(); }} className="space-y-3">
          {aba === "contas" && (
            <>
              <input className="w-full border rounded px-3 py-2 text-sm" placeholder="Nome" value={form.nome || ""} onChange={e => setForm({ ...form, nome: e.target.value })} />
              <input className="w-full border rounded px-3 py-2 text-sm" type="number" step="0.01" placeholder="Saldo inicial" value={form.saldo_inicial || "0"} onChange={e => setForm({ ...form, saldo_inicial: e.target.value })} />
            </>
          )}
          {aba === "transacoes" && (
            <>
              <select className="w-full border rounded px-3 py-2 text-sm" value={form.tipo || "despesa"} onChange={e => setForm({ ...form, tipo: e.target.value })}>
                <option value="despesa">Despesa</option>
                <option value="receita">Receita</option>
              </select>
              <input className="w-full border rounded px-3 py-2 text-sm" type="number" step="0.01" placeholder="Valor" value={form.valor || ""} onChange={e => setForm({ ...form, valor: e.target.value })} />
              <input className="w-full border rounded px-3 py-2 text-sm" placeholder="Descrição" value={form.descricao || ""} onChange={e => setForm({ ...form, descricao: e.target.value })} />
              <select className="w-full border rounded px-3 py-2 text-sm" value={form.conta || ""} onChange={e => setForm({ ...form, conta: e.target.value })}>
                <option value="">Selecione a conta</option>
                {contas.map(c => <option key={c.id} value={c.id}>{c.nome}</option>)}
              </select>
              <select className="w-full border rounded px-3 py-2 text-sm" value={form.categoria || ""} onChange={e => setForm({ ...form, categoria: e.target.value })}>
                <option value="">Selecione a categoria</option>
                {categorias.map(c => <option key={c.id} value={c.id}>{c.nome}</option>)}
              </select>
            </>
          )}
          {aba === "categorias" && (
            <>
              <input className="w-full border rounded px-3 py-2 text-sm" placeholder="Nome" value={form.nome || ""} onChange={e => setForm({ ...form, nome: e.target.value })} />
              <select className="w-full border rounded px-3 py-2 text-sm" value={form.tipo || "despesa"} onChange={e => setForm({ ...form, tipo: e.target.value })}>
                <option value="despesa">Despesa</option>
                <option value="receita">Receita</option>
              </select>
            </>
          )}
          {aba === "apagar" && (
            <>
              <input className="w-full border rounded px-3 py-2 text-sm" placeholder="Descrição (ex.: Aluguel)" value={form.descricao || ""} onChange={e => setForm({ ...form, descricao: e.target.value })} />
              <input className="w-full border rounded px-3 py-2 text-sm" type="number" step="0.01" placeholder="Valor" value={form.valor || ""} onChange={e => setForm({ ...form, valor: e.target.value })} />
              <label className="block text-xs text-gray-500">Vencimento
                <input className="w-full border rounded px-3 py-2 text-sm mt-1" type="date" value={form.vencimento || ""} onChange={e => setForm({ ...form, vencimento: e.target.value })} />
              </label>
              <label className="flex items-center gap-2 text-sm text-gray-600">
                <input type="checkbox" checked={form.recorrencia || false} onChange={e => setForm({ ...form, recorrencia: e.target.checked })} />
                Recorrente (todo mês)
              </label>
            </>
          )}
          {aba === "metas" && (
            <>
              <input className="w-full border rounded px-3 py-2 text-sm" placeholder="Nome da meta (ex.: Viagem)" value={form.nome || ""} onChange={e => setForm({ ...form, nome: e.target.value })} />
              <input className="w-full border rounded px-3 py-2 text-sm" type="number" step="0.01" placeholder="Valor alvo" value={form.valor_alvo || ""} onChange={e => setForm({ ...form, valor_alvo: e.target.value })} />
              <label className="block text-xs text-gray-500">Prazo (opcional)
                <input className="w-full border rounded px-3 py-2 text-sm mt-1" type="date" value={form.prazo || ""} onChange={e => setForm({ ...form, prazo: e.target.value })} />
              </label>
            </>
          )}
          {aba === "consultores" && (
            <>
              <input className="w-full border rounded px-3 py-2 text-sm" type="email" placeholder="E-mail do consultor" value={form.consultor_email || ""} onChange={e => setForm({ ...form, consultor_email: e.target.value })} />
              <select className="w-full border rounded px-3 py-2 text-sm" value={form.nivel || "leitura"} onChange={e => setForm({ ...form, nivel: e.target.value })}>
                <option value="leitura">Leitura — só visualiza minhas finanças</option>
                <option value="comentar">Comentar — visualiza e deixa recomendações</option>
              </select>
            </>
          )}
          <button type="button" onClick={() => {
            const endpoint = aba === "contas" ? "/contas/"
              : aba === "transacoes" ? "/transacoes/"
              : aba === "categorias" ? "/categorias/"
              : aba === "apagar" ? "/contas-a-pagar/"
              : aba === "metas" ? "/metas/"
              : "/autorizacoes/";
            const dados = { ...form };
            if (aba === "metas" && !dados.prazo) delete dados.prazo;
            salvar(endpoint, dados);
          }} className="w-full bg-indigo-600 text-white rounded-lg py-2 text-sm hover:bg-indigo-700">
            Salvar
          </button>
        </form>
      </Modal>
    </div>
  );
}
