export default function Pagination({ page, pageSize, count, onPageChange }) {
  const totalPaginas = Math.max(1, Math.ceil(count / pageSize));
  if (totalPaginas <= 1) return null;

  return (
    <div className="flex items-center justify-between gap-3 px-3 py-3 border-t border-slate-100 text-sm">
      <span className="text-slate-400">
        {count} {count === 1 ? "registro" : "registros"} · página {page} de {totalPaginas}
      </span>
      <div className="flex gap-2">
        <button type="button" onClick={() => onPageChange(page - 1)} disabled={page <= 1}
          className="btn-ghost px-3 py-1.5 text-xs disabled:opacity-40 disabled:pointer-events-none">
          ← Anterior
        </button>
        <button type="button" onClick={() => onPageChange(page + 1)} disabled={page >= totalPaginas}
          className="btn-ghost px-3 py-1.5 text-xs disabled:opacity-40 disabled:pointer-events-none">
          Próxima →
        </button>
      </div>
    </div>
  );
}
