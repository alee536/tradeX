interface LogoProps {
  showText?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export function Logo({ showText = true, size = 'md' }: LogoProps) {
  const sizeClasses = {
    sm: 'w-6 h-6',
    md: 'w-8 h-8',
    lg: 'w-10 h-10',
  };

  const textSize = {
    sm: 'text-sm',
    md: 'text-base',
    lg: 'text-lg',
  };

  return (
    <div className="flex items-center gap-2">
      <img
        src={`${import.meta.env.BASE_URL}logo.png`}
        alt="TRADEX Logo"
        className={`${sizeClasses[size]} shrink-0`}
      />
      {showText && (
        <span className={`text-white font-bold ${textSize[size]}`}>
          TRADEX
        </span>
      )}
    </div>
  );
}
