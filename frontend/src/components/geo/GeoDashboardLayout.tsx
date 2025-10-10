import { ReactNode } from 'react'
import { Tabs, TabsList, TabsTrigger } from '../../components/ui/tabs'

const TABS = [
  { id: 'overview', label: 'Visão Geral', description: 'KPIs e panorama geral' },
  { id: 'citations', label: 'Citações', description: 'Distribuição por produto e funil' },
  { id: 'competitors', label: 'Concorrentes', description: 'Share of voice e qualidade' },
  { id: 'citability', label: 'Citabilidade', description: 'Drivers e recomendações' },
  { id: 'content', label: 'Conteúdo', description: 'Lacunas e próximos passos' },
]

export type GeoDashboardLayoutProps = {
  currentTab: string
  onTabChange: (tabId: string) => void
  children: ReactNode
}

export function GeoDashboardLayout({ currentTab, onTabChange, children }: GeoDashboardLayoutProps) {
  return (
    <div className="space-y-6">
      <Tabs value={currentTab} onValueChange={onTabChange}>
        <TabsList className="flex w-full flex-wrap items-center justify-center gap-4 bg-transparent px-2 py-2">
          {TABS.map((tab) => (
            <TabsTrigger
              key={tab.id}
              value={tab.id}
              className="group inline-flex min-w-[150px] max-w-[220px] flex-col gap-1 rounded-2xl border border-transparent px-6 py-3 text-center text-sm font-medium text-slate-600 transition hover:border-blue-100 hover:bg-blue-50/40 hover:text-blue-600 data-[state=active]:border-blue-500/80 data-[state=active]:bg-white data-[state=active]:text-blue-700 data-[state=active]:shadow-md"
            >
              <span>{tab.label}</span>
              <span className="text-xs font-normal text-slate-500 group-hover:text-blue-500/80 data-[state=active]:text-blue-600/80 leading-tight">
                {tab.description}
              </span>
            </TabsTrigger>
          ))}
        </TabsList>
        {children}
      </Tabs>
    </div>
  )
}
