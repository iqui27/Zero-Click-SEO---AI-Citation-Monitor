import { ReactNode } from 'react';
import { clsx } from 'clsx';

interface PrismBackgroundProps {
  children: ReactNode;
  className?: string;
  overlayClassName?: string;
}

export default function PrismBackground({
  children,
  className = '',
  overlayClassName = '',
}: PrismBackgroundProps) {
  return (
    <div
      className={clsx(
        'relative min-h-screen overflow-hidden bg-gradient-to-br from-[#f5f8ff] via-[#eef3ff] to-[#fbfdff]',
        className,
      )}
    >
      <div className={clsx('pointer-events-none absolute inset-0', overlayClassName)}>
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(96,165,250,0.18),_rgba(245,248,255,0))]" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_bottom_right,_rgba(191,219,254,0.18),_rgba(245,248,255,0))]" />

        <div className="absolute -left-1/2 top-[-20%] h-[120%] w-[90%] rotate-[-10deg] bg-[linear-gradient(125deg,_rgba(59,130,246,0.16)_0%,_rgba(165,180,252,0.12)_45%,_rgba(255,255,255,0)_100%)] blur-[100px]" />
        <div className="absolute -right-1/3 bottom-[-35%] h-[130%] w-[85%] rotate-[8deg] bg-[linear-gradient(140deg,_rgba(148,163,184,0.16)_0%,_rgba(56,189,248,0.18)_50%,_rgba(255,255,255,0)_100%)] blur-[110px]" />

        <div className="absolute left-1/2 top-1/2 h-[150%] w-[150%] -translate-x-1/2 -translate-y-1/2 animate-[spin_55s_linear_infinite] bg-[conic-gradient(from_140deg_at_50%_50%,rgba(191,219,254,0.35),rgba(56,189,248,0.25),rgba(148,163,184,0.2),rgba(191,219,254,0.35))] opacity-55 blur-[160px]" />

        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_rgba(255,255,255,0.45),_rgba(245,248,255,0.65))]" />
      </div>

      <div className={clsx('relative z-10', className)}>{children}</div>
    </div>
  );
}
