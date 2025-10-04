import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Badge } from "../ui/badge";
import { TrendingUp, TrendingDown, Minus, LucideIcon } from "lucide-react";

interface MetricCardProps {
  title: string;
  value: number | null;
  min?: number | null;
  max?: number | null;
  trend?: number | null;
  icon: LucideIcon;
  color?: "blue" | "purple" | "green" | "orange" | "red";
  subtitle?: string;
}

const colorClasses = {
  blue: "text-blue-600 bg-blue-50",
  purple: "text-purple-600 bg-purple-50",
  green: "text-green-600 bg-green-50",
  orange: "text-orange-600 bg-orange-50",
  red: "text-red-600 bg-red-50",
};

export function MetricCard({
  title,
  value,
  min,
  max,
  trend,
  icon: Icon,
  color = "blue",
  subtitle,
}: MetricCardProps) {
  const getTrendIcon = () => {
    if (trend === null || trend === undefined) return null;
    if (trend > 0) return <TrendingUp className="w-4 h-4 text-green-600" />;
    if (trend < 0) return <TrendingDown className="w-4 h-4 text-red-600" />;
    return <Minus className="w-4 h-4 text-gray-400" />;
  };

  const getTrendColor = () => {
    if (trend === null || trend === undefined) return "secondary";
    if (trend > 0) return "default";
    if (trend < 0) return "destructive";
    return "secondary";
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <div className={`p-2 rounded-lg ${colorClasses[color]}`}>
          <Icon className="w-4 h-4" />
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          <div className="text-3xl font-bold">
            {value !== null && value !== undefined
              ? value.toFixed(1)
              : "N/A"}
          </div>
          {subtitle && (
            <p className="text-xs text-muted-foreground">{subtitle}</p>
          )}
          
          {/* Min/Max */}
          {(min !== null && min !== undefined) || (max !== null && max !== undefined) ? (
            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              {min !== null && min !== undefined && (
                <div className="flex items-center gap-1">
                  <span className="font-medium">Min:</span>
                  <span>{min.toFixed(1)}</span>
                </div>
              )}
              {max !== null && max !== undefined && (
                <div className="flex items-center gap-1">
                  <span className="font-medium">Max:</span>
                  <span>{max.toFixed(1)}</span>
                </div>
              )}
            </div>
          ) : null}
          
          {/* Trend */}
          {trend !== null && trend !== undefined && (
            <div className="flex items-center gap-1">
              {getTrendIcon()}
              <Badge variant={getTrendColor()} className="text-xs">
                {trend > 0 ? "+" : ""}
                {trend.toFixed(1)}%
              </Badge>
              <span className="text-xs text-muted-foreground">
                vs período anterior
              </span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
