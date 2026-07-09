import { useCallback, useState } from "react";

export const USAGE_PAGE_SIZE_KEY = "quotahub-usage-page-size";
export const DEFAULT_USAGE_PAGE_SIZE = 20;
export const USAGE_PAGE_SIZE_OPTIONS = [20, 50, 100] as const;

export type UsagePageSize = (typeof USAGE_PAGE_SIZE_OPTIONS)[number];

function parseStoredPageSize(value: string | null): UsagePageSize {
  const parsed = Number(value);
  if (USAGE_PAGE_SIZE_OPTIONS.includes(parsed as UsagePageSize)) {
    return parsed as UsagePageSize;
  }
  return DEFAULT_USAGE_PAGE_SIZE;
}

export function loadUsagePageSize(): UsagePageSize {
  try {
    return parseStoredPageSize(localStorage.getItem(USAGE_PAGE_SIZE_KEY));
  } catch {
    return DEFAULT_USAGE_PAGE_SIZE;
  }
}

export function saveUsagePageSize(size: UsagePageSize): void {
  try {
    localStorage.setItem(USAGE_PAGE_SIZE_KEY, String(size));
  } catch {
    /* ignore */
  }
}

export function useUsagePageSize(): [UsagePageSize, (size: UsagePageSize) => void] {
  const [pageSize, setPageSizeState] = useState<UsagePageSize>(loadUsagePageSize);

  const setPageSize = useCallback((size: UsagePageSize) => {
    setPageSizeState(size);
    saveUsagePageSize(size);
  }, []);

  return [pageSize, setPageSize];
}

export function buildPageItems(
  totalPages: number,
  currentPage: number,
  siblingCount = 2
): Array<number | "ellipsis"> {
  if (totalPages <= 1) return [1];

  const maxWithoutEllipsis = siblingCount * 2 + 5;
  if (totalPages <= maxWithoutEllipsis) {
    return Array.from({ length: totalPages }, (_, index) => index + 1);
  }

  const items: Array<number | "ellipsis"> = [1];
  const start = Math.max(2, currentPage - siblingCount);
  const end = Math.min(totalPages - 1, currentPage + siblingCount);

  if (start > 2) items.push("ellipsis");
  for (let page = start; page <= end; page += 1) {
    items.push(page);
  }
  if (end < totalPages - 1) items.push("ellipsis");
  items.push(totalPages);

  return items;
}
