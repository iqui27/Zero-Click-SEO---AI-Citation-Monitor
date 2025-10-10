import { ReactNode, useState } from 'react';

interface GlowCardProps {
  children: ReactNode;
  glowColor?: string;
  intensity?: number;
  className?: string;
}

export default function GlowCard({
  children,
  glowColor = 'rgba(168, 85, 247, 0.4)',
  intensity = 20,
  className = '',
}: GlowCardProps) {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <div
      className={`relative ${className}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {isHovered && (
        <div
          className="absolute inset-0 rounded-inherit blur-xl transition-all duration-500 -z-10 animate-pulse"
          style={{
            background: glowColor,
            filter: `blur(${intensity}px)`,
          }}
        />
      )}
      {children}
    </div>
  );
}
