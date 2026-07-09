import { useCallback, useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { UsagePagination } from "@/components/usage/UsagePagination";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api, type AllUsageListResponse } from "@/lib/api";
import { useUsagePageSize } from "@/lib/usage-pagination";

function formatCost(usd: number): string {
  if (usd < 0.01) return `$${usd.toFixed(6)}`;
  return `$${usd.toFixed(4)}`;
}

export default function AllUsagePage() {
  const [data, setData] = useState<AllUsageListResponse | null>(null);
  const [offset, setOffset] = useState(0);
  const [accountId, setAccountId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [pageSize, setPageSize] = useUsagePageSize();

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const result = await api.listAllUsage({
        offset,
        limit: pageSize,
        account_id: accountId || undefined,
      });
      setData(result);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [offset, accountId, pageSize]);

  useEffect(() => {
    void load();
  }, [load]);

  const total = data?.total ?? 0;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <CardTitle className="text-base">使用记录 · 共 {total} 条</CardTitle>
        <div className="flex flex-wrap items-center gap-2">
          {data?.accounts && data.accounts.length > 0 && (
            <Select
              value={accountId || "__all__"}
              onValueChange={(value) => {
                setAccountId(value === "__all__" ? "" : value);
                setOffset(0);
              }}
            >
              <SelectTrigger className="h-9 w-[14rem] [&>span]:truncate">
                <SelectValue placeholder="全部账号" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">全部账号</SelectItem>
                {data.accounts.map((account) => (
                  <SelectItem key={account.id} value={account.id}>
                    {account.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <div className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {error}
          </div>
        )}

        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>时间</TableHead>
              <TableHead>账号</TableHead>
              <TableHead>模型</TableHead>
              <TableHead>Provider</TableHead>
              <TableHead className="text-right">Input</TableHead>
              <TableHead className="text-right">Output</TableHead>
              <TableHead className="text-right">费用</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading && !data?.records.length ? (
              <TableRow>
                <TableCell colSpan={7} className="py-8 text-center text-muted-foreground">
                  加载中…
                </TableCell>
              </TableRow>
            ) : data?.records.length ? (
              data.records.map((row) => (
                <TableRow key={row.usg_id}>
                  <TableCell className="whitespace-nowrap text-xs">
                    {new Date(row.created_at).toLocaleString("zh-CN")}
                  </TableCell>
                  <TableCell className="text-sm font-medium">{row.account_name}</TableCell>
                  <TableCell>{row.model}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">{row.provider || "—"}</TableCell>
                  <TableCell className="text-right tabular-nums">{row.input_tokens.toLocaleString()}</TableCell>
                  <TableCell className="text-right tabular-nums">{row.output_tokens.toLocaleString()}</TableCell>
                  <TableCell className="text-right tabular-nums">{formatCost(row.cost_usd)}</TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={7} className="py-8 text-center text-muted-foreground">
                  暂无记录
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>

        <UsagePagination
          total={total}
          offset={offset}
          pageSize={pageSize}
          loading={loading}
          onOffsetChange={setOffset}
          onPageSizeChange={(size) => {
            setPageSize(size);
            setOffset(0);
          }}
        />
      </CardContent>
    </Card>
  );
}
