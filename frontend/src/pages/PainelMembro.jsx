import { useState, useEffect, useCallback, useRef } from "react";
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from "recharts";
import api from "../api/client";
import { extrairErro } from "../api/erros";
import { useAuth } from "../contexts/AuthContext";
import Modal from "../components/Modal";

// Paleta categórica validada (CVD-safe, ordem fixa — dataviz)
const COLORS = ["#2a78d6", "#1baf7a", "#eda100", "#008300", "#4a3aa7", "#e34948", "#e87ba4", "#eb6834"];
const COR_OUTROS = "#898781";

function formatMoney(v) {
  return Number(v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
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
  useEffect(() => { load("/transacoes/?page_size=100", setTransacoes); }, [load]);
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
      load(endpoint === "/transacoes/" ? "/transacoes/?page_size=100" : endpoint, setters[endpoint]);
      if (endpoint === "/transacoes/") load("/contas/", setContas); // saldo vivo
    } catch (err) {
      setMsg({ tipo: "erro", texto: extrairErro(err, "Erro ao salvar.") });
    }
  };

  const deletar = async (endpoint, id, setter) => {
    if (!confirm("Confirmar exclusão?")) return;
    try {
      await api.delete(`${endpoint}${id}/`);
      load(endpoint === "/transacoes/" ? "/transacoes/?page_size=100" : endpoint, setter);
      if (endpoint === "/transacoes/") load("/contas/", setContas); // saldo vivo
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
      load("/transacoes/?page_size=100", setTransacoes);
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
      load("/transacoes/?page_size=100", setTransacoes);
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

  // Dados para gráfico — categorias em ordem de valor; além de 7, agrupa em "Outros"
  const despesasPorCat = transacoes
    .filter(t => t.tipo === "despesa")
    .reduce((acc, t) => {
      const nome = t.nome_categoria || "Sem categoria";
      acc[nome] = (acc[nome] || 0) + Number(t.valor);
      return acc;
    }, {});
  const ordenadas = Object.entries(despesasPorCat).sort((a, b) => b[1] - a[1]);
  const principais = ordenadas.slice(0, 7).map(([name, value]) => ({ name, value }));
  const resto = ordenadas.slice(7).reduce((s, [, v]) => s + v, 0);
  const graficoData = resto > 0 ? [...principais, { name: "Outros", value: resto }] : principais;
  const totalDespesas = graficoData.reduce((s, d) => s + d.value, 0);

  const saldoTotal = contas.reduce((s, c) => s + Number(c.saldo_atual ?? c.saldo_inicial ?? 0), 0);
  const aPagarAbertas = contasAPagar.filter(c => !c.pago);
  const metasConcluidas = metas.filter(m => m.concluida).length;
  const consultoresAtivos = autorizacoes.filter(a => a.cliente === user?.id && a.status).length;

  const tiles = [
    { label: "Saldo total", valor: formatMoney(saldoTotal), icone: "💳", cor: saldoTotal < 0 ? "text-red-600" : "text-emerald-600" },
    { label: "A pagar em aberto", valor: `${aPagarAbertas.length} · ${formatMoney(aPagarAbertas.reduce((s, c) => s + Number(c.valor), 0))}`, icone: "📅", cor: "text-slate-800" },
    { label: "Metas concluídas", valor: `${metasConcluidas} de ${metas.length}`, icone: "🎯", cor: "text-slate-800" },
    { label: "Consultores ativos", valor: String(consultoresAtivos), icone: "🤝", cor: "text-slate-800" },
  ];

  return (
    <div>
      <div className="mb-5">
        <h2 className="text-2xl font-bold text-slate-800">Olá, {user?.nome?.split(" ")[0]} 👋</h2>
        <p className="text-sm text-slate-400">Aqui está o resumo das suas finanças.</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {tiles.map(t => (
          <div key={t.label} className="card p-4 flex items-center gap-3">
            <span className="grid place-items-center w-10 h-10 rounded-xl bg-indigo-50 text-lg shrink-0">{t.icone}</span>
            <div className="min-w-0">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 truncate">{t.label}</p>
              <p className={`font-bold tnum truncate ${t.cor}`}>{t.valor}</p>
            </div>
          </div>
        ))}
      </div>

      {msg && (
        <div className={msg.tipo === "erro" ? "banner-erro" : "banner-ok"}>
          <span className="flex-1">{msg.texto}</span>
          <button onClick={() => setMsg(null)} className="font-bold px-1 opacity-60 hover:opacity-100">×</button>
        </div>
      )}

      <div className="tabs">
        {abas.map(a => (
          <button key={a.key} onClick={() => setAba(a.key)}
            className={aba === a.key ? "tab-active" : "tab"}>
            {a.label}
          </button>
        ))}
      </div>

      {/* Contas */}
      {aba === "contas" && (
        <div>
          <div className="flex justify-between items-center mb-3">
            <h3 className="font-semibold">Minhas Contas</h3>
            <button onClick={() => abrirModal()} className="btn-primary">
              + Nova Conta
            </button>
          </div>
          <div className="card overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr><th className="p-3">Nome</th><th className="p-3">Saldo Inicial</th><th className="p-3">Saldo Atual</th><th className="p-3">Ativa</th><th className="p-3"></th></tr>
              </thead>
              <tbody>
                {contas.map(c => (
                  <tr key={c.id}>
                    <td className="p-3 font-medium">{c.nome}</td>
                    <td className="p-3">{formatMoney(c.saldo_inicial)}</td>
                    <td className={`p-3 font-medium ${Number(c.saldo_atual) < 0 ? "text-red-600" : "text-green-600"}`}>{formatMoney(c.saldo_atual)}</td>
                    <td className="p-3">{c.ativa ? "Sim" : "Não"}</td>
                    <td className="p-3 flex gap-2">
                      <button onClick={() => abrirModal(c)} className="btn-mini-indigo">Editar</button>
                      <button onClick={() => deletar("/contas/", c.id, setContas)} className="btn-mini-red">Excluir</button>
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
              <button onClick={() => abrirModal()} className="btn-primary">
                + Nova Transação
              </button>
            </div>
          </div>
          <div className="card overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr><th className="p-3">Descrição</th><th className="p-3">Valor</th><th className="p-3">Conta</th><th className="p-3">Categoria</th><th className="p-3">Data</th><th className="p-3"></th></tr>
              </thead>
              <tbody>
                {transacoes.map(t => (
                  <tr key={t.id}>
                    <td className="p-3 font-medium">{t.descricao || t.tipo}</td>
                    <td className={`p-3 font-medium ${t.tipo === "receita" ? "text-green-600" : "text-red-600"}`}>
                      {t.tipo === "receita" ? "+" : "-"}{formatMoney(t.valor)}
                    </td>
                    <td className="p-3">{t.nome_conta}</td>
                    <td className="p-3">{t.nome_categoria}</td>
                    <td className="p-3">{new Date(t.data).toLocaleDateString("pt-BR")}</td>
                    <td className="p-3 flex gap-2">
                      <button onClick={() => abrirModal(t)} className="btn-mini-indigo">Editar</button>
                      <button onClick={() => deletar("/transacoes/", t.id, setTransacoes)} className="btn-mini-red">Excluir</button>
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
            <button onClick={() => abrirModal()} className="btn-primary">
              + Nova Categoria
            </button>
          </div>
          <div className="card overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr><th className="p-3">Nome</th><th className="p-3">Tipo</th><th className="p-3">Padrão</th><th className="p-3"></th></tr>
              </thead>
              <tbody>
                {categorias.map(c => (
                  <tr key={c.id}>
                    <td className="p-3 font-medium">{c.nome}</td>
                    <td className="p-3 capitalize">{c.tipo}</td>
                    <td className="p-3">{c.padrao ? "Sim" : "Não"}</td>
                    <td className="p-3 flex gap-2">
                      {!c.padrao && (
                        <>
                          <button onClick={() => abrirModal(c)} className="btn-mini-indigo">Editar</button>
                          <button onClick={() => deletar("/categorias/", c.id, setCategorias)} className="btn-mini-red">Excluir</button>
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
            <button onClick={() => abrirModal()} className="btn-primary">
              + Nova Conta a Pagar
            </button>
          </div>
          <div className="card overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr><th className="p-3">Descrição</th><th className="p-3">Valor</th><th className="p-3">Vencimento</th><th className="p-3">Status</th><th className="p-3"></th></tr>
              </thead>
              <tbody>
                {contasAPagar.map(c => {
                  const vencida = !c.pago && new Date(c.vencimento + "T23:59:59") < new Date();
                  return (
                    <tr key={c.id}>
                      <td className="p-3 font-medium">{c.descricao}{c.recorrencia ? " 🔁" : ""}</td>
                      <td className="p-3">{formatMoney(c.valor)}</td>
                      <td className="p-3">{new Date(c.vencimento + "T12:00:00").toLocaleDateString("pt-BR")}</td>
                      <td className="p-3">
                        {c.pago
                          ? <span className="badge-green">✓ Paga</span>
                          : vencida
                            ? <span className="badge-red">! Vencida</span>
                            : <span className="badge-amber">Em aberto</span>}
                      </td>
                      <td className="p-3 flex gap-2">
                        {!c.pago && (
                          <button onClick={async () => {
                            setMsg(null);
                            try {
                              await api.post(`/contas-a-pagar/${c.id}/pagar/`);
                              load("/contas-a-pagar/", setContasAPagar);
                              load("/contas/", setContas);
                              load("/transacoes/?page_size=100", setTransacoes);
                              setMsg({ tipo: "ok", texto: `"${c.descricao}" paga — despesa lançada e saldo atualizado.` });
                            } catch (err) {
                              setMsg({ tipo: "erro", texto: extrairErro(err, "Erro ao pagar.") });
                            }
                          }} className="btn-mini-green">Marcar paga</button>
                        )}
                        <button onClick={() => abrirModal(c)} className="btn-mini-indigo">Editar</button>
                        <button onClick={() => deletar("/contas-a-pagar/", c.id, setContasAPagar)} className="btn-mini-red">Excluir</button>
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
            <button onClick={() => abrirModal()} className="btn-primary">
              + Nova Meta
            </button>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            {metas.map(m => (
              <div key={m.id} className="card p-4">
                <div className="flex justify-between items-start mb-2">
                  <h4 className="font-semibold">{m.nome} {m.concluida && <span className="text-green-600 text-xs ml-1">✓ concluída</span>}</h4>
                  <button onClick={() => deletar("/metas/", m.id, setMetas)} className="btn-mini-red">Excluir</button>
                </div>
                <p className="text-sm text-gray-500 mb-2">
                  {formatMoney(m.valor_atual)} de {formatMoney(m.valor_alvo)}
                  {m.prazo && ` — até ${new Date(m.prazo + "T12:00:00").toLocaleDateString("pt-BR")}`}
                </p>
                <div className="progress-track mb-3">
                  <div className={`progress-fill ${m.concluida ? "bg-emerald-500" : "bg-gradient-to-r from-indigo-500 to-violet-500"}`} style={{ width: `${m.percentual}%` }} />
                </div>
                <div className="flex items-center justify-between">
                  <button onClick={() => aportar(m)} className="btn-primary text-xs px-3 py-1.5">
                    + Guardar dinheiro
                  </button>
                  <span className="text-xs font-semibold text-slate-400 tnum">{m.percentual}%</span>
                </div>
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
              <button onClick={() => abrirModal()} className="btn-primary">
                + Autorizar Consultor
              </button>
            </div>
            <div className="card overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr><th className="p-3">Consultor</th><th className="p-3">E-mail</th><th className="p-3">Nível</th><th className="p-3">Status</th><th className="p-3"></th></tr>
                </thead>
                <tbody>
                  {autorizacoes.filter(a => a.cliente === user?.id).map(a => (
                    <tr key={a.id}>
                      <td className="p-3 font-medium">{a.nome_consultor}</td>
                      <td className="p-3">{a.email_consultor}</td>
                      <td className="p-3"><span className="badge-indigo capitalize">{a.nivel}</span></td>
                      <td className="p-3">
                        {a.status
                          ? <span className="badge-green">● Ativa</span>
                          : <span className="badge-gray">Revogada</span>}
                      </td>
                      <td className="p-3">
                        {a.status
                          ? <button onClick={() => revogarAutorizacao(a)} className="btn-mini-red">Revogar</button>
                          : <button onClick={() => reativarAutorizacao(a)} className="btn-mini-green">Reativar</button>}
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
                <div key={r.id} className="card p-4">
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
        <div className="card p-6">
          <div className="flex items-baseline justify-between flex-wrap gap-2 mb-1">
            <h3 className="font-semibold text-slate-800">Despesas por categoria</h3>
            <p className="text-sm text-slate-400">Total: <span className="font-semibold text-slate-600 tnum">{formatMoney(totalDespesas)}</span></p>
          </div>
          <p className="text-xs text-slate-400 mb-4">Somando as despesas mais recentes; categorias menores agrupadas em "Outros".</p>
          {graficoData.length > 0 ? (
            <ResponsiveContainer width="100%" height={360}>
              <PieChart>
                <Pie data={graficoData} dataKey="value" nameKey="name" cx="50%" cy="50%"
                  innerRadius={75} outerRadius={120} paddingAngle={2}
                  stroke="#ffffff" strokeWidth={2}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                  {graficoData.map((d, i) => (
                    <Cell key={i} fill={d.name === "Outros" ? COR_OUTROS : COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v) => formatMoney(v)}
                  contentStyle={{ borderRadius: 12, border: "1px solid #e2e8f0", boxShadow: "0 4px 12px rgba(15,23,42,.08)", fontSize: 13 }} />
                <Legend iconType="circle" iconSize={9} wrapperStyle={{ fontSize: 13, color: "#52514e" }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="text-center py-14">
              <p className="text-4xl mb-2">📊</p>
              <p className="text-slate-400">Nenhuma despesa registrada ainda.</p>
              <button onClick={() => setAba("transacoes")} className="btn-ghost mt-4">Lançar minha primeira transação</button>
            </div>
          )}
        </div>
      )}

      {/* Modal CRUD */}
      <Modal isOpen={modalOpen} onClose={() => { setModalOpen(false); setEditando(null); }}
        title={editando ? `Editar ${editando.nome || editando.descricao || ""}` : "Novo"}>
        <form onSubmit={(e) => { e.preventDefault(); }} className="space-y-3">
          {aba === "contas" && (
            <>
              <input className="input" placeholder="Nome" value={form.nome || ""} onChange={e => setForm({ ...form, nome: e.target.value })} />
              <input className="input" type="number" step="0.01" placeholder="Saldo inicial" value={form.saldo_inicial || "0"} onChange={e => setForm({ ...form, saldo_inicial: e.target.value })} />
            </>
          )}
          {aba === "transacoes" && (
            <>
              <select className="input" value={form.tipo || "despesa"} onChange={e => setForm({ ...form, tipo: e.target.value })}>
                <option value="despesa">Despesa</option>
                <option value="receita">Receita</option>
              </select>
              <input className="input" type="number" step="0.01" placeholder="Valor" value={form.valor || ""} onChange={e => setForm({ ...form, valor: e.target.value })} />
              <input className="input" placeholder="Descrição" value={form.descricao || ""} onChange={e => setForm({ ...form, descricao: e.target.value })} />
              <select className="input" value={form.conta || ""} onChange={e => setForm({ ...form, conta: e.target.value })}>
                <option value="">Selecione a conta</option>
                {contas.map(c => <option key={c.id} value={c.id}>{c.nome}</option>)}
              </select>
              <select className="input" value={form.categoria || ""} onChange={e => setForm({ ...form, categoria: e.target.value })}>
                <option value="">Selecione a categoria</option>
                {categorias.map(c => <option key={c.id} value={c.id}>{c.nome}</option>)}
              </select>
            </>
          )}
          {aba === "categorias" && (
            <>
              <input className="input" placeholder="Nome" value={form.nome || ""} onChange={e => setForm({ ...form, nome: e.target.value })} />
              <select className="input" value={form.tipo || "despesa"} onChange={e => setForm({ ...form, tipo: e.target.value })}>
                <option value="despesa">Despesa</option>
                <option value="receita">Receita</option>
              </select>
            </>
          )}
          {aba === "apagar" && (
            <>
              <input className="input" placeholder="Descrição (ex.: Aluguel)" value={form.descricao || ""} onChange={e => setForm({ ...form, descricao: e.target.value })} />
              <input className="input" type="number" step="0.01" placeholder="Valor" value={form.valor || ""} onChange={e => setForm({ ...form, valor: e.target.value })} />
              <label className="block text-xs text-gray-500">Vencimento
                <input className="input mt-1" type="date" value={form.vencimento || ""} onChange={e => setForm({ ...form, vencimento: e.target.value })} />
              </label>
              <label className="flex items-center gap-2 text-sm text-gray-600">
                <input type="checkbox" checked={form.recorrencia || false} onChange={e => setForm({ ...form, recorrencia: e.target.checked })} />
                Recorrente (todo mês)
              </label>
            </>
          )}
          {aba === "metas" && (
            <>
              <input className="input" placeholder="Nome da meta (ex.: Viagem)" value={form.nome || ""} onChange={e => setForm({ ...form, nome: e.target.value })} />
              <input className="input" type="number" step="0.01" placeholder="Valor alvo" value={form.valor_alvo || ""} onChange={e => setForm({ ...form, valor_alvo: e.target.value })} />
              <label className="block text-xs text-gray-500">Prazo (opcional)
                <input className="input mt-1" type="date" value={form.prazo || ""} onChange={e => setForm({ ...form, prazo: e.target.value })} />
              </label>
            </>
          )}
          {aba === "consultores" && (
            <>
              <input className="input" type="email" placeholder="E-mail do consultor" value={form.consultor_email || ""} onChange={e => setForm({ ...form, consultor_email: e.target.value })} />
              <select className="input" value={form.nivel || "leitura"} onChange={e => setForm({ ...form, nivel: e.target.value })}>
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
          }} className="btn-primary w-full">
            Salvar
          </button>
        </form>
      </Modal>
    </div>
  );
}
