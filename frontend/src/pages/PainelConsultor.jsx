import { useState, useEffect, useCallback } from "react";
import api from "../api/client";
import { useAuth } from "../contexts/AuthContext";
import Modal from "../components/Modal";

function formatMoney(v) {
  return Number(v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export default function PainelConsultor() {
  const { user } = useAuth();
  const [clientes, setClientes] = useState([]);
  const [clienteSel, setClienteSel] = useState(null);
  const [transacoes, setTransacoes] = useState([]);
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

  const carregarCliente = async (clienteId) => {
    setClienteSel(clienteId);
    try {
      const [t, c, rec] = await Promise.all([
        api.get(`/consultor/clientes/${clienteId}/transacoes/`),
        api.get(`/consultor/clientes/${clienteId}/contas/`),
        api.get("/recomendacoes/"),
      ]);
      setTransacoes(t.data.results || []);
      setContas(c.data.results || []);
      setRecomendacoes((rec.data.results || []).filter(r => r.cliente === clienteId));
    } catch { }
  };

  const criarRecomendacao = async () => {
    try {
      await api.post("/recomendacoes/", {
        cliente: clienteSel,
        texto: form.texto,
      });
      setModalOpen(false);
      setMsg("Recomendação enviada!");
      carregarCliente(clienteSel);
    } catch (e) {
      setMsg(e.response?.data?.detail || "Erro ao criar recomendação.");
    }
  };

  const criarAutorizacao = async () => {
    try {
      await api.post("/autorizacoes/", form);
      setModalOpen(false);
      setMsg("Autorização criada! O consultor já pode visualizar seus dados.");
    } catch (e) {
      setMsg(e.response?.data?.detail || JSON.stringify(e.response?.data) || "Erro.");
    }
  };

  const revogarAutorizacao = async (id) => {
    if (!confirm("Revogar esta autorização?")) return;
    await api.delete(`/autorizacoes/${id}/`);
    loadClientes();
  };

  return (
    <div>
      <h2 className="text-xl font-bold mb-2">Painel do Consultor — {user?.nome}</h2>
      {msg && (
        <div className={`p-2 rounded text-sm mb-3 ${msg.includes("Erro") ? "bg-red-100 text-red-800" : "bg-green-100 text-green-800"}`}>
          {msg}
        </div>
      )}

      <div className="flex gap-2 mb-4 border-b">
        <button onClick={() => setClienteSel(null)}
          className={`px-4 py-2 text-sm font-medium rounded-t-lg ${!clienteSel ? "bg-white border border-b-white -mb-px text-indigo-600" : "text-gray-500"}`}>
          Meus Clientes
        </button>
        {clienteSel && (
          <button className="px-4 py-2 text-sm font-medium rounded-t-lg bg-white border border-b-white -mb-px text-indigo-600">
            Detalhes do Cliente
          </button>
        )}
      </div>

      {!clienteSel && (
        <div>
          <div className="flex gap-2 mb-3">
            <button onClick={() => { setForm({ consultor: "", nivel: "leitura" }); setModalTipo("autorizacao"); setModalOpen(true); }}
              className="bg-indigo-600 text-white px-3 py-1.5 rounded text-sm hover:bg-indigo-700">
              + Autorizar Consultor
            </button>
          </div>
          {clientes.length === 0 ? (
            <p className="text-gray-400">Nenhum cliente autorizado ainda.</p>
          ) : (
            <div className="grid gap-3">
              {clientes.map(c => (
                <div key={c.id} className="bg-white rounded-lg shadow p-4 flex justify-between items-center cursor-pointer hover:shadow-md"
                  onClick={() => carregarCliente(c.id)}>
                  <div>
                    <h4 className="font-semibold">{c.nome}</h4>
                    <p className="text-sm text-gray-500">{c.email}</p>
                  </div>
                  <span className="text-xs text-indigo-600">Ver finanças →</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {clienteSel && (
        <div>
          <div className="flex gap-3 mb-4 border-b pb-2">
            {["transacoes", "contas", "recomendacoes"].map(k => (
              <button key={k} onClick={() => setClienteSel(c => c ? { ...c, aba: k } : null)}
                className={`text-sm px-3 py-1 rounded ${(clienteSel.aba || "transacoes") === k ? "bg-indigo-100 text-indigo-700 font-medium" : "text-gray-500"}`}>
                {k === "transacoes" ? "Transações" : k === "contas" ? "Contas" : "Recomendações"}
              </button>
            ))}
          </div>

          {(clienteSel.aba || "transacoes") === "transacoes" && (
            <div className="bg-white rounded-lg shadow overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50"><tr><th className="p-3">Descrição</th><th className="p-3">Valor</th><th className="p-3">Tipo</th><th className="p-3">Data</th></tr></thead>
                <tbody>
                  {transacoes.map(t => (
                    <tr key={t.id} className="border-t">
                      <td className="p-3">{t.descricao || t.tipo}</td>
                      <td className={`p-3 font-medium ${t.tipo === "despesa" ? "text-red-600" : "text-green-600"}`}>{formatMoney(t.valor)}</td>
                      <td className="p-3 capitalize">{t.tipo}</td>
                      <td className="p-3">{new Date(t.data).toLocaleDateString("pt-BR")}</td>
                    </tr>
                  ))}
                  {transacoes.length === 0 && <tr><td colSpan={4} className="p-3 text-gray-400 text-center">Nenhuma transação</td></tr>}
                </tbody>
              </table>
            </div>
          )}

          {(clienteSel.aba || "transacoes") === "contas" && (
            <div className="bg-white rounded-lg shadow overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50"><tr><th className="p-3">Nome</th><th className="p-3">Saldo Inicial</th><th className="p-3">Ativa</th></tr></thead>
                <tbody>
                  {contas.map(c => (
                    <tr key={c.id} className="border-t"><td className="p-3 font-medium">{c.nome}</td><td className="p-3">{formatMoney(c.saldo_inicial)}</td><td className="p-3">{c.ativa ? "Sim" : "Não"}</td></tr>
                  ))}
                  {contas.length === 0 && <tr><td colSpan={3} className="p-3 text-gray-400 text-center">Nenhuma conta</td></tr>}
                </tbody>
              </table>
            </div>
          )}

          {(clienteSel.aba || "transacoes") === "recomendacoes" && (
            <div>
              <button onClick={() => { setForm({ texto: "" }); setModalTipo("recomendacao"); setModalOpen(true); }}
                className="bg-indigo-600 text-white px-3 py-1.5 rounded text-sm hover:bg-indigo-700 mb-3">
                + Nova Recomendação
              </button>
              <div className="bg-white rounded-lg shadow overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50"><tr><th className="p-3">Texto</th><th className="p-3">Data</th></tr></thead>
                  <tbody>
                    {recomendacoes.map(r => (
                      <tr key={r.id} className="border-t"><td className="p-3">{r.texto}</td><td className="p-3">{new Date(r.data).toLocaleDateString("pt-BR")}</td></tr>
                    ))}
                    {recomendacoes.length === 0 && <tr><td colSpan={2} className="p-3 text-gray-400 text-center">Nenhuma recomendação</td></tr>}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title={modalTipo === "recomendacao" ? "Nova Recomendação" : "Autorizar Consultor"}>
        {modalTipo === "recomendacao" && (
          <div className="space-y-3">
            <textarea className="w-full border rounded px-3 py-2 text-sm" rows={4} placeholder="Texto da recomendação..." value={form.texto || ""}
              onChange={e => setForm({ ...form, texto: e.target.value })} />
            <button onClick={criarRecomendacao} className="w-full bg-indigo-600 text-white rounded-lg py-2 text-sm hover:bg-indigo-700">Enviar</button>
          </div>
        )}
        {modalTipo === "autorizacao" && (
          <div className="space-y-3">
            <input className="w-full border rounded px-3 py-2 text-sm" type="number" placeholder="ID do consultor" value={form.consultor || ""}
              onChange={e => setForm({ ...form, consultor: e.target.value })} />
            <select className="w-full border rounded px-3 py-2 text-sm" value={form.nivel || "leitura"}
              onChange={e => setForm({ ...form, nivel: e.target.value })}>
              <option value="leitura">Leitura</option>
              <option value="comentar">Comentar</option>
            </select>
            <button onClick={criarAutorizacao} className="w-full bg-indigo-600 text-white rounded-lg py-2 text-sm hover:bg-indigo-700">Autorizar</button>
          </div>
        )}
      </Modal>
    </div>
  );
}
