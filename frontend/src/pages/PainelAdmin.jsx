import { useState, useEffect, useCallback } from "react";
import api from "../api/client";
import { extrairErro } from "../api/erros";
import { useAuth } from "../contexts/AuthContext";
import Modal from "../components/Modal";
import Pagination from "../components/Pagination";

const PAGE_SIZE = 20;

export default function PainelAdmin() {
  const { user } = useAuth();
  const [aba, setAba] = useState("usuarios");
  const [usuarios, setUsuarios] = useState([]);
  const [usuariosPage, setUsuariosPage] = useState(1);
  const [usuariosCount, setUsuariosCount] = useState(0);
  const [categorias, setCategorias] = useState([]);
  const [categoriasPage, setCategoriasPage] = useState(1);
  const [categoriasCount, setCategoriasCount] = useState(0);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalTipo, setModalTipo] = useState("");
  const [editando, setEditando] = useState(null);
  const [form, setForm] = useState({});
  const [msg, setMsg] = useState(null); // { tipo: "ok" | "erro", texto }

  const loadUsuarios = useCallback(async (page = 1) => {
    try {
      const r = await api.get(`/usuarios/?page=${page}&page_size=${PAGE_SIZE}`);
      setUsuarios(r.data.results || []);
      setUsuariosCount(r.data.count || 0);
      setUsuariosPage(page);
    } catch { }
  }, []);
  const loadCategorias = useCallback(async (page = 1) => {
    try {
      const r = await api.get(`/categorias/?page=${page}&page_size=${PAGE_SIZE}`);
      setCategorias(r.data.results || []);
      setCategoriasCount(r.data.count || 0);
      setCategoriasPage(page);
    } catch { }
  }, []);

  useEffect(() => { loadUsuarios(1); loadCategorias(1); }, [loadUsuarios, loadCategorias]);

  const salvarUsuario = async () => {
    setMsg(null);
    const dados = { ...form };
    if (!dados.senha) delete dados.senha; // na edição, senha em branco = não alterar
    try {
      if (editando) {
        await api.patch(`/usuarios/${editando.id}/`, dados);
      } else {
        await api.post("/usuarios/", dados);
      }
      setModalOpen(false); setEditando(null); loadUsuarios(editando ? usuariosPage : 1);
      setMsg({ tipo: "ok", texto: "Usuário salvo." });
    } catch (err) {
      setMsg({ tipo: "erro", texto: extrairErro(err, "Erro ao salvar o usuário.") });
    }
  };

  const deletarUsuario = async (u) => {
    if (!confirm(`Excluir ${u.nome} (${u.email})? Todos os dados financeiros dele serão apagados. Se quiser apenas bloquear o acesso, edite e desmarque "Ativo".`)) return;
    setMsg(null);
    try {
      await api.delete(`/usuarios/${u.id}/`);
      loadUsuarios(usuarios.length <= 1 && usuariosPage > 1 ? usuariosPage - 1 : usuariosPage);
      setMsg({ tipo: "ok", texto: `Usuário ${u.nome} excluído.` });
    } catch (err) {
      setMsg({ tipo: "erro", texto: extrairErro(err, "Erro ao excluir o usuário.") });
    }
  };

  const salvarCategoria = async () => {
    setMsg(null);
    try {
      if (editando) {
        await api.patch(`/categorias/${editando.id}/`, form);
      } else {
        await api.post("/categorias/", form);
      }
      setModalOpen(false); setEditando(null); loadCategorias(editando ? categoriasPage : 1);
      setMsg({ tipo: "ok", texto: "Categoria salva." });
    } catch (err) {
      setMsg({ tipo: "erro", texto: extrairErro(err, "Erro ao salvar a categoria.") });
    }
  };

  const deletarCategoria = async (c) => {
    if (!confirm(`Excluir a categoria padrão "${c.nome}"?`)) return;
    setMsg(null);
    try {
      await api.delete(`/categorias/${c.id}/`);
      loadCategorias(categorias.length <= 1 && categoriasPage > 1 ? categoriasPage - 1 : categoriasPage);
      setMsg({ tipo: "ok", texto: `Categoria "${c.nome}" excluída.` });
    } catch (err) {
      setMsg({ tipo: "erro", texto: extrairErro(err, "Erro ao excluir a categoria.") });
    }
  };

  return (
    <div>
      <div className="mb-5">
        <h2 className="text-2xl font-bold text-slate-800">Administração 🛠️</h2>
        <p className="text-sm text-slate-400">
          Aqui você gerencia a plataforma: contas de usuários (criar, ativar/desativar, excluir) e as
          categorias padrão que todos veem. O admin não participa das finanças — por isso não tem painel financeiro.
        </p>
      </div>
      {msg && (
        <div className={msg.tipo === "erro" ? "banner-erro" : "banner-ok"}>
          <span className="flex-1">{msg.texto}</span>
          <button onClick={() => setMsg(null)} className="font-bold px-1 opacity-60 hover:opacity-100">×</button>
        </div>
      )}

      <div className="tabs">
        {["usuarios", "categorias"].map(k => (
          <button key={k} onClick={() => setAba(k)} className={aba === k ? "tab-active" : "tab"}>
            {k === "usuarios" ? "Usuários" : "Categorias Padrão"}
          </button>
        ))}
      </div>

      {aba === "usuarios" && (
        <div>
          <button onClick={() => { setEditando(null); setForm({ email: "", nome: "", senha: "", papel_sistema: "comum", is_active: true }); setModalTipo("usuario"); setModalOpen(true); }}
            className="btn-primary mb-3">+ Novo Usuário</button>
          <div className="card overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr><th className="p-3">Nome</th><th className="p-3">Email</th><th className="p-3">Papel</th><th className="p-3">Ativo</th><th className="p-3"></th></tr></thead>
              <tbody>
                {usuarios.map(u => (
                  <tr key={u.id}>
                    <td className="p-3 font-medium">{u.nome}{u.id === user?.id && <span className="text-xs text-slate-400 ml-1">(você)</span>}</td>
                    <td className="p-3">{u.email}</td>
                    <td className="p-3">{u.papel_sistema === "admin" ? <span className="badge-indigo">Admin</span> : <span className="badge-gray">Comum</span>}</td>
                    <td className="p-3">{u.is_active ? <span className="badge-green">● Ativo</span> : <span className="badge-red">Inativo</span>}</td>
                    <td className="p-3 flex gap-2">
                      <button onClick={() => { setEditando(u); setForm({ email: u.email, nome: u.nome, senha: "", papel_sistema: u.papel_sistema, is_active: u.is_active }); setModalTipo("usuario"); setModalOpen(true); }}
                        className="btn-mini-indigo">Editar</button>
                      {u.id !== user?.id && (
                        <button onClick={() => deletarUsuario(u)} className="btn-mini-red">Excluir</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <Pagination page={usuariosPage} pageSize={PAGE_SIZE} count={usuariosCount} onPageChange={loadUsuarios} />
          </div>
        </div>
      )}

      {aba === "categorias" && (
        <div>
          <p className="text-xs text-slate-400 mb-3">
            Categorias padrão aparecem para todos os usuários. Uma categoria em uso por transações ou orçamentos não pode ser excluída.
          </p>
          <button onClick={() => { setEditando(null); setForm({ nome: "", tipo: "despesa" }); setModalTipo("categoria"); setModalOpen(true); }}
            className="btn-primary mb-3">+ Nova Categoria Padrão</button>
          <div className="card overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr><th className="p-3">Nome</th><th className="p-3">Tipo</th><th className="p-3"></th></tr></thead>
              <tbody>
                {categorias.map(c => (
                  <tr key={c.id}>
                    <td className="p-3 font-medium">{c.nome}</td>
                    <td className="p-3">{c.tipo === "despesa" ? <span className="badge-red">Despesa</span> : <span className="badge-green">Receita</span>}</td>
                    <td className="p-3 flex gap-2">
                      <button onClick={() => { setEditando(c); setForm({ nome: c.nome, tipo: c.tipo }); setModalTipo("categoria"); setModalOpen(true); }}
                        className="btn-mini-indigo">Editar</button>
                      <button onClick={() => deletarCategoria(c)} className="btn-mini-red">Excluir</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <Pagination page={categoriasPage} pageSize={PAGE_SIZE} count={categoriasCount} onPageChange={loadCategorias} />
          </div>
        </div>
      )}

      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title={editando ? "Editar" : "Novo"}>
        {modalTipo === "usuario" && (
          <div className="space-y-3">
            <input className="input" placeholder="Nome" value={form.nome || ""} onChange={e => setForm({ ...form, nome: e.target.value })} />
            <input className="input" placeholder="Email" value={form.email || ""} onChange={e => setForm({ ...form, email: e.target.value })} />
            <input className="input" type="password"
              placeholder={editando ? "Nova senha (deixe em branco para manter)" : "Senha (mínimo 6 caracteres)"}
              value={form.senha || ""} onChange={e => setForm({ ...form, senha: e.target.value })} />
            <select className="input" value={form.papel_sistema || "comum"} onChange={e => setForm({ ...form, papel_sistema: e.target.value })}>
              <option value="comum">Comum</option>
              <option value="admin">Administrador</option>
            </select>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={form.is_active !== false} onChange={e => setForm({ ...form, is_active: e.target.checked })} /> Ativo
            </label>
            <button onClick={salvarUsuario} className="btn-primary w-full">Salvar</button>
          </div>
        )}
        {modalTipo === "categoria" && (
          <div className="space-y-3">
            <input className="input" placeholder="Nome" value={form.nome || ""} onChange={e => setForm({ ...form, nome: e.target.value })} />
            <select className="input" value={form.tipo || "despesa"} onChange={e => setForm({ ...form, tipo: e.target.value })}>
              <option value="despesa">Despesa</option>
              <option value="receita">Receita</option>
            </select>
            <button onClick={salvarCategoria} className="btn-primary w-full">Salvar</button>
          </div>
        )}
      </Modal>
    </div>
  );
}
