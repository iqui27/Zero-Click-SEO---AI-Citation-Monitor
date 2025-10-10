import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { getProjects, type Project } from '../lib/api'
import { Card, CardContent } from '../components/ui/card'
import { UnifiedGeoDashboard } from '../components/geo/UnifiedGeoDashboard'
import { Button } from '../components/ui/button'
import { Select } from '../components/ui/select'
import { Skeleton } from '../components/ui/skeleton'

export default function GEODashboard() {
  const [projects, setProjects] = useState<Project[]>([])
  const [selectedProjectId, setSelectedProjectId] = useState<string>('')
  const [searchParams, setSearchParams] = useSearchParams()
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    getProjects()
      .then((items) => {
        setProjects(items)
        const projectIdParam = searchParams.get('project_id')
        if (projectIdParam) {
          setSelectedProjectId(projectIdParam)
        } else if (items.length > 0) {
          const defaultProjectId = items[0].id
          setSelectedProjectId(defaultProjectId)
          setSearchParams((prev) => {
            const params = new URLSearchParams(prev)
            params.set('project_id', defaultProjectId)
            return params
          })
        }
        setIsLoading(false)
      })
      .catch(() => {
        setProjects([])
        setIsLoading(false)
      })
  }, [])

  useEffect(() => {
    const projectIdParam = searchParams.get('project_id')
    if (projectIdParam && projectIdParam !== selectedProjectId) {
      setSelectedProjectId(projectIdParam)
    }
  }, [searchParams])

  const handleProjectChange = (projectId: string) => {
    setSelectedProjectId(projectId)
    setSearchParams((prev) => {
      const params = new URLSearchParams(prev)
      if (projectId) {
        params.set('project_id', projectId)
      } else {
        params.delete('project_id')
      }
      return params
    })
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-20" />
        <Skeleton className="h-96" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <span className="uppercase tracking-[0.3em] text-xs text-blue-500 font-semibold">GEO Dashboard</span>
          <h1 className="text-3xl md:text-4xl font-semibold text-slate-900 mt-2">AI Citation Monitor</h1>
          <p className="text-sm text-slate-500 mt-2">
            Acompanhe menções de marca, citações e share of voice em experiências LLM.
          </p>
        </div>
        <div className="flex flex-wrap gap-3 items-center">
          <Select value={selectedProjectId} onChange={(e) => handleProjectChange(e.target.value)}>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </Select>
          <Button variant="outline" onClick={() => window.location.reload()}>
            Atualizar dados
          </Button>
        </div>
      </header>

      {!selectedProjectId ? (
        <Card>
          <CardContent className="p-6 text-sm text-slate-500">
            Selecione um projeto para visualizar o dashboard GEO.
          </CardContent>
        </Card>
      ) : (
        <UnifiedGeoDashboard projectId={selectedProjectId} />
      )}
    </div>
  )
}
