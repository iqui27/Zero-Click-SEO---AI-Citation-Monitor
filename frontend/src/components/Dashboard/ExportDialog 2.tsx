import { useState } from "react";
import { Button } from "../ui/button";
import { Download, FileText, FileJson, FileSpreadsheet } from "lucide-react";
import { FilterState } from "./Filters";

interface ExportDialogProps {
  filters: FilterState;
  totalRecords: number;
}

export function ExportDialog({ filters, totalRecords }: ExportDialogProps) {
  const [exporting, setExporting] = useState(false);
  const [format, setFormat] = useState<"csv" | "json" | "excel">("csv");
  const [includeMetadata, setIncludeMetadata] = useState(true);

  const buildExportUrl = (exportFormat: string) => {
    const params = new URLSearchParams();
    
    params.append("days", filters.days.toString());
    if (filters.project_id) params.append("project_id", filters.project_id);
    if (filters.engine_ids && filters.engine_ids.length > 0) {
      params.append("engine_ids", filters.engine_ids.join(","));
    }
    if (filters.start_date) params.append("start_date", filters.start_date);
    if (filters.end_date) params.append("end_date", filters.end_date);
    if (filters.im_seo_min !== undefined) params.append("im_seo_min", filters.im_seo_min.toString());
    if (filters.im_seo_max !== undefined) params.append("im_seo_max", filters.im_seo_max.toString());
    if (filters.im_seoia_min !== undefined) params.append("im_seoia_min", filters.im_seoia_min.toString());
    if (filters.im_seoia_max !== undefined) params.append("im_seoia_max", filters.im_seoia_max.toString());
    
    if (exportFormat !== "excel") {
      params.append("include_metadata", includeMetadata.toString());
    }
    
    return `/api/export/${exportFormat}?${params.toString()}`;
  };

  const handleExport = async () => {
    setExporting(true);
    
    try {
      const url = buildExportUrl(format);
      
      // Criar link temporário e clicar
      const link = document.createElement("a");
      link.href = url;
      link.download = `export_${Date.now()}.${format === "excel" ? "xlsx" : format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      // Feedback visual
      setTimeout(() => {
        setExporting(false);
      }, 1000);
    } catch (error) {
      console.error("Error exporting:", error);
      setExporting(false);
      alert("Erro ao exportar dados. Tente novamente.");
    }
  };

  const getFormatIcon = () => {
    switch (format) {
      case "csv":
        return <FileText className="w-5 h-5" />;
      case "json":
        return <FileJson className="w-5 h-5" />;
      case "excel":
        return <FileSpreadsheet className="w-5 h-5" />;
    }
  };

  const getFormatDescription = () => {
    switch (format) {
      case "csv":
        return "Arquivo CSV compatível com Excel, Google Sheets, etc.";
      case "json":
        return "Formato JSON estruturado para APIs e análise programática.";
      case "excel":
        return "Planilha Excel (.xlsx) com formatação e estilos.";
    }
  };

  return (
    <div className="space-y-4">
      {/* Formato */}
      <div>
        <label className="text-sm font-medium mb-3 block">Formato de Exportação</label>
        <div className="grid grid-cols-3 gap-3">
          <button
            onClick={() => setFormat("csv")}
            className={`p-4 border-2 rounded-lg flex flex-col items-center gap-2 transition-all ${
              format === "csv"
                ? "border-blue-500 bg-blue-50"
                : "border-gray-200 hover:border-gray-300"
            }`}
          >
            <FileText className="w-8 h-8" />
            <span className="font-medium">CSV</span>
          </button>
          
          <button
            onClick={() => setFormat("json")}
            className={`p-4 border-2 rounded-lg flex flex-col items-center gap-2 transition-all ${
              format === "json"
                ? "border-blue-500 bg-blue-50"
                : "border-gray-200 hover:border-gray-300"
            }`}
          >
            <FileJson className="w-8 h-8" />
            <span className="font-medium">JSON</span>
          </button>
          
          <button
            onClick={() => setFormat("excel")}
            className={`p-4 border-2 rounded-lg flex flex-col items-center gap-2 transition-all ${
              format === "excel"
                ? "border-blue-500 bg-blue-50"
                : "border-gray-200 hover:border-gray-300"
            }`}
          >
            <FileSpreadsheet className="w-8 h-8" />
            <span className="font-medium">Excel</span>
          </button>
        </div>
        <p className="text-xs text-muted-foreground mt-2">
          {getFormatDescription()}
        </p>
      </div>

      {/* Opções */}
      {format !== "excel" && (
        <div>
          <label className="text-sm font-medium mb-2 block">Opções</label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={includeMetadata}
              onChange={(e) => setIncludeMetadata(e.target.checked)}
              className="rounded"
            />
            Incluir metadados (filtros aplicados, data de exportação, etc)
          </label>
        </div>
      )}

      {/* Info */}
      <div className="p-4 bg-gray-50 rounded-lg">
        <div className="text-sm space-y-1">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Total de registros:</span>
            <span className="font-medium">{totalRecords}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Formato:</span>
            <span className="font-medium">{format.toUpperCase()}</span>
          </div>
          {filters.project_id && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">Projeto filtrado:</span>
              <span className="font-medium">Sim</span>
            </div>
          )}
        </div>
      </div>

      {/* Botão de Exportar */}
      <Button
        onClick={handleExport}
        disabled={exporting || totalRecords === 0}
        className="w-full"
        size="lg"
      >
        {exporting ? (
          <>
            <Download className="w-5 h-5 mr-2 animate-bounce" />
            Exportando...
          </>
        ) : (
          <>
            {getFormatIcon()}
            <span className="ml-2">
              Exportar {totalRecords} {totalRecords === 1 ? "registro" : "registros"}
            </span>
          </>
        )}
      </Button>

      {totalRecords === 0 && (
        <p className="text-sm text-center text-muted-foreground">
          Nenhum registro para exportar com os filtros atuais
        </p>
      )}
    </div>
  );
}
