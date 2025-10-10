import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'

export function ContentTab() {
  return (
    <div className="grid gap-6">
      <Card className="border-slate-200">
        <CardHeader>
          <CardTitle className="text-base">Adequação de Conteúdo</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-slate-500 space-y-2">
          <p>
            Em breve esta seção apresentará métricas estruturadas sobre presença de Schema, FAQs, tabelas e outros
            elementos críticos para Zero-Click. Enquanto os dados são acoplados ao pipeline, utilize o painel de GEO
            para identificar prioridades de conteúdo.
          </p>
        </CardContent>
      </Card>

      <Card className="border-dashed border-slate-200">
        <CardHeader>
          <CardTitle className="text-base">Lacunas Detectadas</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-slate-500">
          As lacunas estrutradas por URL serão exibidas aqui quando as integrações com Gemini e crawling automático
          estiverem concluídas. Por hora, recomendamos acompanhar as recomendações descritas nas abas de Visão Geral e
          Citações.
        </CardContent>
      </Card>
    </div>
  )
}
