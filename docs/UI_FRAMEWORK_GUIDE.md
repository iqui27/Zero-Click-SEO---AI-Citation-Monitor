# UI Framework & Layout Documentation

## Framework Overview

Este projeto utiliza um stack moderno de UI baseado em:

- **Next.js 15** - Framework React com App Router
- **Tailwind CSS v4** - Framework CSS utility-first
- **shadcn/ui** - Biblioteca de componentes baseada em Radix UI
- **Geist Font** - Tipografia moderna (Sans e Mono)
- **Class Variance Authority (CVA)** - Gerenciamento de variantes de componentes

## Design System

### Paleta de Cores

O sistema utiliza CSS custom properties com valores OKLCH para melhor consistência de cores:

#### Cores Principais
\`\`\`css
--primary: oklch(0.205 0 0)           /* Preto/Branco principal */
--secondary: oklch(0.97 0 0)          /* Cinza claro */
--accent: oklch(0.97 0 0)             /* Cor de destaque */
--destructive: oklch(0.577 0.245 27.325) /* Vermelho para ações destrutivas */
\`\`\`

#### Cores de Superfície
\`\`\`css
--background: oklch(1 0 0)            /* Fundo principal */
--card: oklch(1 0 0)                  /* Fundo de cards */
--popover: oklch(1 0 0)               /* Fundo de popovers */
--border: oklch(0.922 0 0)            /* Bordas */
\`\`\`

#### Modo Escuro
Todas as cores possuem variantes para modo escuro automaticamente aplicadas via `.dark` class.

### Tipografia

#### Fontes
- **Geist Sans** - Fonte principal para textos e interfaces
- **Geist Mono** - Fonte monoespaçada para código

#### Hierarquia Tipográfica
\`\`\`css
/* Headings */
text-2xl font-semibold    /* H1 - Títulos principais */
text-lg font-medium       /* H2 - Subtítulos */
text-base font-medium     /* H3 - Seções */

/* Body Text */
text-sm                   /* Texto padrão */
text-xs                   /* Texto secundário/labels */
\`\`\`

### Espaçamento

#### Sistema de Grid
- **Container**: `max-w-[1200px] mx-auto` - Largura máxima centralizada
- **Padding**: `px-3 sm:px-4 md:px-6` - Responsivo
- **Gap**: `gap-3` (12px) para elementos relacionados, `gap-6` (24px) para seções

#### Breakpoints
\`\`\`css
sm: 640px   /* Tablet pequeno */
md: 768px   /* Tablet */
lg: 1024px  /* Desktop */
xl: 1280px  /* Desktop grande */
\`\`\`

## Componentes UI

### Button Component

Localização: `components/ui/button.tsx`

#### Variantes
\`\`\`tsx
variant: {
  default: "bg-primary text-primary-foreground"     // Botão principal
  destructive: "bg-destructive text-white"          // Ações destrutivas
  outline: "border bg-background"                   // Botão secundário
  secondary: "bg-secondary text-secondary-foreground" // Botão terciário
  ghost: "hover:bg-accent"                          // Botão transparente
  link: "text-primary underline-offset-4"           // Link estilizado
}

size: {
  default: "h-9 px-4 py-2"    // Tamanho padrão
  sm: "h-8 px-3"              // Pequeno
  lg: "h-10 px-6"             // Grande
  icon: "size-9"              // Apenas ícone
}
\`\`\`

#### Uso
\`\`\`tsx
<Button variant="default" size="lg">Botão Principal</Button>
<Button variant="outline">Botão Secundário</Button>
<Button variant="ghost" size="sm">Ação Sutil</Button>
\`\`\`

### Card Component

Padrão para containers de conteúdo:

\`\`\`tsx
function Card({ title, value }: { title: string; value: React.ReactNode }) {
  return (
    <div className="border border-neutral-200 dark:border-neutral-800 rounded-lg p-4">
      <div className="text-xs text-neutral-500">{title}</div>
      <div className="text-2xl font-bold">{value}</div>
    </div>
  )
}
\`\`\`

## Padrões de Layout

### 1. Container Principal
\`\`\`tsx
<div className="space-y-4 px-3 sm:px-4 md:px-6 max-w-[1200px] mx-auto">
  {/* Conteúdo */}
</div>
\`\`\`

### 2. Grid de Cards/Métricas
\`\`\`tsx
<div className="grid lg:grid-cols-5 gap-3">
  <Card title="Métrica 1" value="100" />
  <Card title="Métrica 2" value="200" />
</div>
\`\`\`

### 3. Seções com Títulos
\`\`\`tsx
<section className="space-y-2">
  <h2 className="text-lg font-medium">Título da Seção</h2>
  <div className="space-y-3">
    {/* Conteúdo da seção */}
  </div>
</section>
\`\`\`

### 4. Layout Responsivo
\`\`\`tsx
<div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
  {/* Items que se adaptam ao tamanho da tela */}
</div>
\`\`\`

## Estados e Interações

### Estados de Loading
\`\`\`tsx
<div className="text-sm opacity-70">Carregando...</div>
\`\`\`

### Estados de Status
\`\`\`tsx
const statusColors = {
  ok: 'text-green-600',
  started: 'text-blue-600', 
  error: 'text-red-600',
  idle: 'text-neutral-500'
}
\`\`\`

### Badges/Tags
\`\`\`tsx
<span className="px-2 py-0.5 border rounded-md text-xs">
  Label
</span>

<span className="px-2 py-0.5 border rounded-md bg-green-50 dark:bg-green-900/20">
  Status Ativo
</span>
\`\`\`

## Utilitários

### Função `cn()` 
Localização: `lib/utils.ts`

Combina classes Tailwind condicionalmente:
\`\`\`tsx
import { cn } from "@/lib/utils"

<div className={cn(
  "base-classes",
  condition && "conditional-classes",
  variant === 'primary' && "primary-classes"
)} />
\`\`\`

### Ícones
Utiliza **Lucide React** para ícones consistentes:
\`\`\`tsx
import { Search, Bot, Camera, Globe } from 'lucide-react'

<Search className="h-4 w-4" />
\`\`\`

## Boas Práticas

### 1. Consistência de Espaçamento
- Use `space-y-*` para espaçamento vertical entre elementos
- Use `gap-*` em containers flex/grid
- Mantenha proporções: `gap-2` (8px), `gap-3` (12px), `gap-4` (16px)

### 2. Responsividade
- Sempre comece mobile-first
- Use breakpoints semânticos: `sm:`, `md:`, `lg:`
- Teste em diferentes tamanhos de tela

### 3. Acessibilidade
- Use cores com contraste adequado
- Adicione `alt` em imagens
- Use elementos semânticos (`<section>`, `<article>`, `<nav>`)

### 4. Performance
- Use `loading="lazy"` em imagens
- Minimize re-renders com `useMemo`/`useCallback`
- Otimize imports de ícones

### 5. Manutenibilidade
- Extraia componentes reutilizáveis
- Use o sistema de design tokens (CSS variables)
- Documente componentes complexos
- Mantenha consistência nos nomes de classes

## Estrutura de Arquivos

\`\`\`
├── app/
│   ├── layout.tsx          # Layout raiz com fontes
│   ├── page.tsx           # Página principal
│   └── globals.css        # Estilos globais e tokens
├── components/
│   ├── ui/                # Componentes base (shadcn/ui)
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   └── ...
│   └── [ComponentName].tsx # Componentes específicos
├── lib/
│   └── utils.ts           # Utilitários (cn function)
└── hooks/                 # Custom hooks
    ├── use-mobile.tsx
    └── use-toast.ts
\`\`\`

Este guia deve ser seguido para manter consistência visual e funcional em todo o projeto.
