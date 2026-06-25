import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatResetIn(seconds: number): string {
  if (seconds <= 0) return "即将重置";
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);

  if (days > 0) {
    return `${days}天${hours}小时${minutes}分钟后重置`;
  }
  if (hours > 0) return `${hours} 小时 ${minutes} 分钟后重置`;
  if (minutes > 0) return `${minutes} 分钟后重置`;
  return `${seconds} 秒后重置`;
}

export function quotaLabel(label: string): string {
  switch (label) {
    case "5h Rolling":
      return "5 小时滚动";
    case "Weekly":
      return "周额度";
    case "Monthly":
      return "月额度";
    case "Session":
      return "5 小时限额";
    default:
      return label;
  }
}

export function ollamaQuotaLabel(label: string): string {
  switch (label) {
    case "Session":
      return "5 小时限额";
    case "Weekly":
      return "周限额";
    default:
      return quotaLabel(label);
  }
}

export function formatPlanLabel(plan: string): string {
  const trimmed = plan.trim();
  if (!trimmed) return trimmed;
  return trimmed.charAt(0).toUpperCase() + trimmed.slice(1).toLowerCase();
}

const OLLAMA_MODEL_COLORS = ["#3b82f6", "#6366f1", "#8b5cf6", "#06b6d4", "#10b981", "#f59e0b"];

export function ollamaModelColor(index: number): string {
  return OLLAMA_MODEL_COLORS[index % OLLAMA_MODEL_COLORS.length];
}

export function usageTone(used: number): string {
  if (used >= 90) return "text-rose-600";
  if (used >= 70) return "text-amber-600";
  return "text-cyan-700";
}

export function progressTone(used: number): string {
  if (used >= 90) return "bg-rose-500";
  if (used >= 70) return "bg-amber-500";
  return "bg-gradient-to-r from-cyan-500 to-sky-500";
}
