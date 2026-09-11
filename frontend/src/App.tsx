import { useCallback, useEffect, useRef, useState } from "react";
import { AlertCircle, CheckCircle2, Download, Trash2, Upload, X, Zap } from "lucide-react";

import type {
  DocumentDetail,
  DocumentItem,
  DocumentsResponse,
  Stats,
  UploadResult,
} from "./types";

const API_BASE = "/api/v1";

const fmtSize = (bytes: number | null | undefined): string => {
  if (bytes == null) return "—";
  if (bytes < 1024) return `${bytes} Б`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} КБ`;
  return `${(bytes / 1048576).toFixed(1)} МБ`;
};

const fmtDate = (iso: string | null): string =>
  iso ? new Date(iso).toLocaleString("ru-RU") : "—";

// Форматы, которые сервер принимает (backend/app/schemas/validation.py).
const ACCEPTED = ".pdf,.docx,.xlsx,.pptx,.txt,.md,.jpg,.jpeg,.png";

/* ---------- Toast ---------- */

interface Toast {
  id: number;
  kind: "success" | "dedup" | "error";
  text: string;
}

const TOAST_STYLE: Record<Toast["kind"], string> = {
  success: "bg-emerald-600",
  dedup: "bg-blue-600",
  error: "bg-red-600",
};

function ToastItem({ toast, onClose }: { toast: Toast; onClose: (id: number) => void }) {
  const icon =
    toast.kind === "dedup" ? (
      <Zap size={18} className="mt-0.5 shrink-0" />
    ) : toast.kind === "error" ? (
      <AlertCircle size={18} className="mt-0.5 shrink-0" />
    ) : (
      <CheckCircle2 size={18} className="mt-0.5 shrink-0" />
    );
  return (
    <div
      className={`flex items-start gap-2 rounded-lg px-4 py-3 text-white shadow-lg ${TOAST_STYLE[toast.kind]} max-w-md`}
    >
      {icon}
      <span>{toast.text}</span>
      <button onClick={() => onClose(toast.id)} className="ml-auto shrink-0 opacity-70 hover:opacity-100">
        <X size={16} />
      </button>
    </div>
  );
}

/* ---------- DropZone ---------- */

function DropZone({ file, onPick, onClear }: {
  file: File | null;
  onPick: (f: File) => void;
  onClear: () => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [hover, setHover] = useState(false);

  return (
    <div
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => {
        e.preventDefault();
        setHover(true);
      }}
      onDragLeave={() => setHover(false)}
      onDrop={(e) => {
        e.preventDefault();
        setHover(false);
        if (e.dataTransfer.files.length) onPick(e.dataTransfer.files[0]);
      }}
      className={`cursor-pointer rounded-lg border-2 border-dashed p-5 text-center transition sm:p-8 ${
        hover ? "border-blue-500 bg-blue-50" : "border-slate-300 hover:border-blue-500 hover:bg-blue-50"
      }`}
    >
      <p className="font-medium text-slate-600">Выберите PDF / скан (или перетащите файл сюда)</p>
      {file && (
        <p className="mt-2 text-sm text-blue-600">
          {file.name}
          <button
            onClick={(e) => {
              e.stopPropagation();
              onClear();
            }}
            className="ml-2 text-slate-400 hover:text-slate-700"
          >
            убрать
          </button>
        </p>
      )}
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED}
        className="hidden"
        onChange={(e) => {
          if (e.target.files?.[0]) onPick(e.target.files[0]);
          inputRef.current!.value = "";
        }}
      />
    </div>
  );
}

/* ---------- Кнопки действий над документом ---------- */

function DocActions({ doc, onHistory, onVersion, onArchive }: {
  doc: DocumentItem;
  onHistory: (id: number) => void;
  onVersion: (id: number) => void;
  onArchive: (id: number) => void;
}) {
  return (
    <div className="inline-flex flex-wrap items-center justify-end gap-2">
      <button
        onClick={() => onHistory(doc.id)}
        className="rounded bg-slate-200 px-3 py-1.5 text-slate-700 hover:bg-slate-300"
      >
        История версий
      </button>
      <button
        onClick={() => onVersion(doc.id)}
        disabled={doc.is_deleted}
        className="rounded bg-blue-600 px-3 py-1.5 font-medium text-white hover:bg-blue-700 disabled:opacity-40"
      >
        Новая версия
      </button>
      <button
        onClick={() => onArchive(doc.id)}
        disabled={doc.is_deleted}
        title="В корзину"
        className="rounded bg-red-600 p-2 text-white hover:bg-red-700 disabled:opacity-40"
      >
        <Trash2 size={16} />
      </button>
    </div>
  );
}

/* ---------- Модалка: история версий ---------- */

function HistoryModal({ detail, onClose }: { detail: DocumentDetail; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
      <div
        className="max-h-[80vh] w-full max-w-2xl overflow-auto rounded-lg bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b px-4 py-3 sm:px-6 sm:py-4">
          <h3 className="font-semibold">История версий — {detail.title}</h3>
          <button onClick={onClose} className="text-xl text-slate-400 hover:text-slate-700">
            <X size={20} />
          </button>
        </div>
        <div className="hidden md:block">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-xs uppercase text-slate-600">
            <tr>
              <th className="px-4 py-2 text-left">Версия</th>
              <th className="px-4 py-2 text-left">Файл</th>
              <th className="px-4 py-2 text-left">Размер</th>
              <th className="px-4 py-2 text-left">Комментарий</th>
              <th className="px-4 py-2 text-left">Дата</th>
              <th className="px-4 py-2 text-right">Скачать</th>
            </tr>
          </thead>
          <tbody>
            {detail.versions.map((v) => (
              <tr key={v.id} className="border-t">
                <td className="px-4 py-2 font-semibold">v{v.version_number}</td>
                <td className="px-4 py-2">{v.file_name}</td>
                <td className="px-4 py-2">{fmtSize(v.file_size)}</td>
                <td className="px-4 py-2 text-slate-500">{v.comment ?? "—"}</td>
                <td className="px-4 py-2">{fmtDate(v.created_at)}</td>
                <td className="px-4 py-2 text-right">
                  <a
                    href={v.download_url}
                    className="inline-flex items-center gap-1 text-blue-600 hover:underline"
                  >
                    <Download size={14} /> Скачать
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>

        {/* Мобильные карточки версий */}
        <div className="divide-y md:hidden">
          {detail.versions.map((v) => (
            <div key={v.id} className="space-y-1 p-4">
              <div className="flex items-center justify-between">
                <span className="font-semibold">v{v.version_number}</span>
                <span className="text-sm text-slate-500">{fmtSize(v.file_size)}</span>
              </div>
              <p className="break-all text-sm">{v.file_name}</p>
              <p className="text-sm text-slate-500">{v.comment ?? "—"}</p>
              <p className="text-xs text-slate-400">{fmtDate(v.created_at)}</p>
              <a
                href={v.download_url}
                className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline"
              >
                <Download size={14} /> Скачать
              </a>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ---------- Модалка: новая версия ---------- */

function VersionModal({ docId, onClose, onUploaded, onError }: {
  docId: number;
  onClose: () => void;
  onUploaded: (result: UploadResult) => void;
  onError: (message: string) => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [comment, setComment] = useState("");

  const submit = async () => {
    if (!file) {
      onError("Выберите файл");
      return;
    }
    const fd = new FormData();
    fd.append("file", file);
    if (comment.trim()) fd.append("comment", comment);
    try {
      const res = await fetch(`${API_BASE}/documents/${docId}/versions`, { method: "POST", body: fd });
      if (res.ok) {
        onUploaded(await res.json());
        onClose();
      } else {
        const data = await res.json().catch(() => null);
        onError(data?.detail ?? "Ошибка загрузки");
      }
    } catch {
      onError("Не удалось связаться с сервером");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
      <div
        className="w-full max-w-md rounded-lg bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b px-4 py-3 sm:px-6 sm:py-4">
          <h3 className="font-semibold">Новая версия — документ #{docId}</h3>
          <button onClick={onClose} className="text-xl text-slate-400 hover:text-slate-700">
            <X size={20} />
          </button>
        </div>
        <div className="space-y-4 p-6">
          <input
            type="file"
            accept={ACCEPTED}
            className="w-full rounded border p-2 text-sm"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
          <input
            type="text"
            placeholder="Комментарий к версии"
            className="w-full rounded border border-slate-300 px-3 py-2"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
          />
          <button
            onClick={submit}
            className="w-full rounded bg-blue-600 py-2 text-white hover:bg-blue-700"
          >
            Загрузить версию
          </button>
        </div>
      </div>
    </div>
  );
}

/* ---------- Главный экран ---------- */

export default function App() {
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [docNumber, setDocNumber] = useState("");
  const [showDeleted, setShowDeleted] = useState(false);
  const [historyDetail, setHistoryDetail] = useState<DocumentDetail | null>(null);
  const [versionDocId, setVersionDocId] = useState<number | null>(null);
  const [toasts, setToasts] = useState<Toast[]>([]);

  const pushToast = useCallback((kind: Toast["kind"], text: string) => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, kind, text }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 7000);
  }, []);

  const loadStats = useCallback(async () => {
    const res = await fetch(`${API_BASE}/stats`);
    setStats(await res.json());
  }, []);

  const refresh = useCallback(async () => {
    const qs = showDeleted ? "?include_deleted=true" : "";
    const res = await fetch(`${API_BASE}/documents${qs}`);
    const data: DocumentsResponse = await res.json();
    setDocs(data.documents);
  }, [showDeleted]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  const showUploadResult = (data: UploadResult) => {
    if (data.deduplicated) {
      pushToast(
        "dedup",
        `Внимание: сработала дедупликация! Идентичный файл уже был в системе. ` +
          `Место на диске сэкономлено (${fmtSize(data.bytes_saved)}).`,
      );
    } else {
      pushToast("success", data.document ? "Документ успешно загружен" : "Версия успешно загружена");
    }
  };

  const submitDocument = async () => {
    if (!uploadedFile || !title.trim()) {
      pushToast("error", "Выберите файл и укажите название");
      return;
    }
    const fd = new FormData();
    fd.append("file", uploadedFile);
    fd.append("title", title);
    if (docNumber.trim()) fd.append("document_number", docNumber);
    try {
      const res = await fetch(`${API_BASE}/documents/upload`, { method: "POST", body: fd });
      if (!res.ok) {
        // ответ может быть не-JSON (например, html-страница 413 от nginx)
        const data = await res.json().catch(() => null);
        pushToast("error", data?.detail ?? "Ошибка загрузки");
        return;
      }
      showUploadResult(await res.json());
    } catch {
      pushToast("error", "Не удалось связаться с сервером");
      return;
    }
    setUploadedFile(null);
    setTitle("");
    setDocNumber("");
    refresh();
    loadStats();
  };

  const archiveDoc = async (id: number) => {
    if (!confirm("Отправить документ в корзину?")) return;
    await fetch(`${API_BASE}/documents/${id}`, { method: "DELETE" });
    pushToast("success", "Документ перемещен в архив (корзину)");
    refresh();
    loadStats();
  };

  const openHistory = async (id: number) => {
    const res = await fetch(`${API_BASE}/documents/${id}`);
    setHistoryDetail(await res.json());
  };

  return (
    <div className="min-h-screen bg-slate-100">
      {/* Шапка */}
      <header className="flex flex-wrap items-center justify-between gap-3 bg-slate-800 px-4 py-3 text-white sm:px-6 sm:py-4">
        <h1 className="text-lg font-bold sm:text-xl">Электронный архив документов</h1>
        <div className="flex gap-2 text-sm">
          <span className="rounded-full bg-slate-700 px-3 py-1">
            Объем архива: {stats ? fmtSize(stats.logical_bytes) : "—"}
          </span>
          <span className="rounded-full bg-emerald-600 px-3 py-1">
            Сэкономлено: {stats ? fmtSize(stats.saved_bytes) : "—"}
          </span>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-6 p-4 sm:p-6">
        {/* Зона загрузки */}
        <section className="rounded-lg bg-white p-4 shadow sm:p-6">
          <DropZone
            file={uploadedFile}
            onPick={setUploadedFile}
            onClear={() => setUploadedFile(null)}
          />
          <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
            <input
              type="text"
              placeholder="Название документа"
              className="w-full rounded border border-slate-300 px-3 py-2 sm:min-w-[220px] sm:flex-1"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
            <input
              type="text"
              placeholder="Номер (необяз.)"
              title="Например: ДОГ-2026/01"
              className="w-full rounded border border-slate-300 px-3 py-2 sm:w-64"
              value={docNumber}
              onChange={(e) => setDocNumber(e.target.value)}
            />
            <button
              onClick={submitDocument}
              className="inline-flex items-center justify-center gap-2 rounded bg-blue-600 px-5 py-2 font-medium text-white hover:bg-blue-700"
            >
              <Upload size={16} /> Загрузить
            </button>
          </div>
        </section>

        {/* Реестр */}
        <section className="overflow-hidden rounded-lg bg-white shadow">
          <div className="flex items-center justify-between border-b px-4 py-3 sm:px-6 sm:py-4">
            <h2 className="text-lg font-semibold">Реестр документов</h2>
            <label className="flex items-center gap-2 text-sm text-slate-600">
              <input
                type="checkbox"
                checked={showDeleted}
                onChange={(e) => setShowDeleted(e.target.checked)}
              />
              показать удаленные
            </label>
          </div>
          <div className="hidden md:block">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-600">
              <tr>
                <th className="px-4 py-3 text-left">Номер</th>
                <th className="px-4 py-3 text-left">Название</th>
                <th className="px-4 py-3 text-left">Текущая версия</th>
                <th className="px-4 py-3 text-left">Размер</th>
                <th className="px-4 py-3 text-left">Дата создания</th>
                <th className="px-4 py-3 text-right">Действия</th>
              </tr>
            </thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.id} className={`border-t hover:bg-slate-50 ${d.is_deleted ? "opacity-50" : ""}`}>
                  <td className="px-4 py-3">{d.document_number || "—"}</td>
                  <td className="px-4 py-3 font-medium">{d.title}</td>
                  <td className="px-4 py-3">v{d.current_version?.version_number ?? "—"}</td>
                  <td className="px-4 py-3">{fmtSize(d.current_version?.file_size)}</td>
                  <td className="px-4 py-3">{fmtDate(d.created_at)}</td>
                  <td className="px-4 py-3 text-right">
                    <DocActions
                      doc={d}
                      onHistory={openHistory}
                      onVersion={setVersionDocId}
                      onArchive={archiveDoc}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>

          {/* Мобильные карточки */}
          <div className="divide-y md:hidden">
            {docs.map((d) => (
              <div key={d.id} className={`p-4 ${d.is_deleted ? "opacity-50" : ""}`}>
                <div className="flex items-start justify-between gap-3">
                  <p className="font-medium">{d.title}</p>
                  <p className="shrink-0 text-sm text-slate-500">{d.document_number || "—"}</p>
                </div>
                <p className="mt-1 text-sm text-slate-500">
                  v{d.current_version?.version_number ?? "—"} · {fmtSize(d.current_version?.file_size)} ·{" "}
                  {fmtDate(d.created_at)}
                </p>
                <div className="mt-3">
                  <DocActions
                    doc={d}
                    onHistory={openHistory}
                    onVersion={setVersionDocId}
                    onArchive={archiveDoc}
                  />
                </div>
              </div>
            ))}
          </div>

          {docs.length === 0 && (
            <p className="py-8 text-center text-slate-400">Документов пока нет</p>
          )}
        </section>
      </main>

      {historyDetail && <HistoryModal detail={historyDetail} onClose={() => setHistoryDetail(null)} />}
      {versionDocId !== null && (
        <VersionModal
          docId={versionDocId}
          onClose={() => setVersionDocId(null)}
          onUploaded={(result) => {
            showUploadResult(result);
            refresh();
            loadStats();
          }}
          onError={(message) => pushToast("error", message)}
        />
      )}

      {/* Toasts */}
      <div className="fixed bottom-4 right-4 left-4 z-50 space-y-2 sm:bottom-6 sm:right-6 sm:left-auto">
        {toasts.map((t) => (
          <ToastItem
            key={t.id}
            toast={t}
            onClose={(id) => setToasts((prev) => prev.filter((t) => t.id !== id))}
          />
        ))}
      </div>
    </div>
  );
}