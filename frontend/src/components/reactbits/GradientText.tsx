import { ReactNode } from 'react';

interface GradientTextProps {
  children: ReactNode;
  colors?: string[];
  animationSpeed?: number;
  className?: string;
}

export default function GradientText({
  children,
  colors = ['#ff4040', '#ff40aa', '#a040ff', '#40a0ff', '#40ffaa'],
  animationSpeed = 8,
  className = '',
}: GradientTextProps) {
  const gradientString = colors.join(', ');

  return (
    <span
      className={`bg-clip-text text-transparent ${className}`}
      style={{
        backgroundImage: `linear-gradient(90deg, ${gradientString}, ${colors[0]})`,
        backgroundSize: '200% 100%',
        animation: `gradient-shift ${animationSpeed}s ease infinite`,
      }}
    >
      {children}
      <style>{`
        @keyframes gradient-shift {
          0%, 100% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
        }
      `}</style>
    </span>
  );
}
