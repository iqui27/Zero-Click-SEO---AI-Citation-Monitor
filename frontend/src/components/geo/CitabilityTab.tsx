import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'

export function CitabilityTab() {
  return (
    <div className="grid gap-6">
      <Card className="border-slate-200">
        <CardHeader>
          <CardTitle className="text-base">Drivers de Citabilidade</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-slate-500 space-y-2">
          <p>
            Os fatores de impacto (modelo preditivo) serão disponibilizados nesta seção assim que os modelos de ML
            forem treinados e publicados. Por enquanto, monitoramos os dados GEO observados nas abas acima.
          </p>
          <p>
            Utilize a aba de Citações para acompanhar a evolução do CR corrigido e a aba de Conteúdo para priorizar
            lacunas identificadas manualmente.
          </p>
        </CardContent>
      </Card>

      <Card className="border-dashed border-slate-200">
        <CardHeader>
          <CardTitle className="text-base">Simulações e Oportunidades</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-slate-500">
          Em breve traremos simulações de impacto em CR a partir de ajustes de conteúdo. Enquanto isso, concentre-se em
          melhorar dados estruturados (Schema, FAQs, Tabelas) e revisar o potencial de conversão detectado nas abas de
          Visão Geral e Conteúdo.
        </CardContent>
      </Card>
    </div>
  )
}
