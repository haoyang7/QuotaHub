import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  buildPageItems,
  USAGE_PAGE_SIZE_OPTIONS,
  type UsagePageSize,
} from "@/lib/usage-pagination";

export function UsagePagination({
  total,
  offset,
  pageSize,
  loading,
  onOffsetChange,
  onPageSizeChange,
}: {
  total: number;
  offset: number;
  pageSize: UsagePageSize;
  loading?: boolean;
  onOffsetChange: (offset: number) => void;
  onPageSizeChange: (pageSize: UsagePageSize) => void;
}) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const currentPage = Math.floor(offset / pageSize) + 1;
  const pageItems = buildPageItems(totalPages, currentPage);

  if (total === 0) return null;

  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <span>每页</span>
        <Select
          value={String(pageSize)}
          onValueChange={(value) => onPageSizeChange(Number(value) as UsagePageSize)}
          disabled={loading}
        >
          <SelectTrigger className="h-8 w-[5.5rem]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {USAGE_PAGE_SIZE_OPTIONS.map((size) => (
              <SelectItem key={size} value={String(size)}>
                {size} 条
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <span>
          共 {total} 条 · 第 {currentPage}/{totalPages} 页
        </span>
      </div>

      {totalPages > 1 && (
        <div className="flex w-full justify-end sm:ml-auto sm:w-auto">
          <Pagination>
            <PaginationContent>
            <PaginationItem>
              <PaginationPrevious
                disabled={currentPage <= 1 || loading}
                onClick={() => onOffsetChange(Math.max(0, offset - pageSize))}
              />
            </PaginationItem>
            {pageItems.map((item, index) =>
              item === "ellipsis" ? (
                <PaginationItem key={`ellipsis-${index}`}>
                  <PaginationEllipsis />
                </PaginationItem>
              ) : (
                <PaginationItem key={item}>
                  <PaginationLink
                    isActive={item === currentPage}
                    disabled={loading}
                    onClick={() => onOffsetChange((item - 1) * pageSize)}
                  >
                    {item}
                  </PaginationLink>
                </PaginationItem>
              )
            )}
            <PaginationItem>
              <PaginationNext
                disabled={currentPage >= totalPages || loading}
                onClick={() => onOffsetChange(offset + pageSize)}
              />
            </PaginationItem>
          </PaginationContent>
        </Pagination>
        </div>
      )}
    </div>
  );
}
