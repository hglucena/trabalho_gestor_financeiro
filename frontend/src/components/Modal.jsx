import { createPortal } from "react-dom";

export default function Modal({ isOpen, onClose, title, children }) {
  if (!isOpen) return null;
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4"
      onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6 animate-modal-pop max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-5">
          <h3 className="text-lg font-bold text-slate-800">{title}</h3>
          <button onClick={onClose}
            className="grid place-items-center w-8 h-8 rounded-full text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors text-xl leading-none">
            &times;
          </button>
        </div>
        {children}
      </div>
    </div>,
    document.body
  );
}
