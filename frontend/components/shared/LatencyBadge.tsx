import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

export function LatencyBadge({ ms, className }: { ms: number; className?: string }) {
  const variant = ms < 500 ? "success" : ms < 1000 ? "warning" : "destructive";
  const label = ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${Math.round(ms)}ms`;

  return (
    <Badge variant={variant} className={cn("font-mono", className)}>
      {label}
    </Badge>
  );
}
