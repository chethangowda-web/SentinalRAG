import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

const statusColors: Record<string, "success" | "warning" | "destructive" | "secondary" | "default"> = {
  completed: "success",
  healthy: "success",
  embedded: "success",
  processing: "warning",
  pending: "secondary",
  failed: "destructive",
  error: "destructive",
  uploaded: "default",
};

export function StatusBadge({
  status,
  className,
}: {
  status: string;
  className?: string;
}) {
  const variant = statusColors[status.toLowerCase()] ?? "secondary";
  return (
    <Badge variant={variant} className={cn("capitalize", className)}>
      {status}
    </Badge>
  );
}
