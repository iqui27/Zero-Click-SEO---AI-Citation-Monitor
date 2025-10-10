import { ReactNode } from 'react';
import { clsx } from 'clsx';

interface SegmentedControlOption {
  label: string;
  value: string | number;
  hint?: ReactNode;
}

interface SegmentedControlProps {
  options: SegmentedControlOption[];
  value: string | number;
  onChange: (value: string | number) => void;
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

const sizeMap: Record<NonNullable<SegmentedControlProps['size']>, string> = {
  sm: 'px-1 py-1 gap-1 text-xs',
  md: 'px-1.5 py-1.5 gap-1.5 text-sm',
  lg: 'px-2 py-2 gap-2 text-base',
};

export default function SegmentedControl({
  options,
  value,
  onChange,
  className = '',
  size = 'md',
}: SegmentedControlProps) {
  return (
    <div
      className={clsx(
        'inline-flex w-full items-center rounded-full border border-slate-200 bg-white/80 p-1 backdrop-blur-md transition-colors duration-300',
        'shadow-[0_10px_30px_rgba(15,23,42,0.08)]',
        className,
      )}
    >
      <div className={clsx('flex w-full items-stretch', sizeMap[size])}>
        {options.map((option) => {
          const isActive = option.value === value;

          return (
            <button
              key={option.value}
              type="button"
              onClick={() => onChange(option.value)}
              className={clsx(
                'relative flex flex-1 select-none flex-col items-center justify-center overflow-hidden rounded-full px-4 py-2 text-center font-medium transition-all duration-300 ease-out',
                'focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400/70',
                isActive
                  ? 'text-white shadow-[0_8px_30px_rgba(56,189,248,0.35)]'
                  : 'text-slate-600 hover:text-slate-800',
              )}
            >
              <div
                className={clsx(
                  'absolute inset-0 -z-10 rounded-full opacity-0 transition-opacity duration-300',
                  isActive
                    ? 'opacity-100 bg-gradient-to-r from-sky-500 via-indigo-500 to-blue-600'
                    : 'bg-white/0',
                )}
              />
              <div className="flex items-center gap-2">
                <span>{option.label}</span>
                {option.hint ? (
                  <span className="text-xs font-normal text-white/70">{option.hint}</span>
                ) : null}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
