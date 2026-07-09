import { cn } from "@/lib/utils";

type ToastKind = "success" | "error";

let container: HTMLDivElement | null = null;

function ensureContainer(): HTMLDivElement {
  if (!container) {
    container = document.createElement("div");
    container.className =
      "pointer-events-none fixed bottom-6 right-6 z-[100] flex max-w-sm flex-col gap-2";
    document.body.appendChild(container);
  }
  return container;
}

export function showToast(message: string, kind: ToastKind = "success", durationMs = 2400): void {
  const root = ensureContainer();
  const toast = document.createElement("div");
  toast.className = cn(
    "pointer-events-auto rounded-xl px-4 py-2.5 text-sm shadow-lg transition-all duration-300",
    "animate-in fade-in slide-in-from-bottom-2",
    kind === "success" ? "bg-slate-900 text-white" : "border border-rose-200 bg-rose-50 text-rose-700"
  );
  toast.textContent = message;
  root.appendChild(toast);

  window.setTimeout(() => {
    toast.classList.add("opacity-0", "translate-y-1");
    window.setTimeout(() => toast.remove(), 300);
  }, durationMs);
}
