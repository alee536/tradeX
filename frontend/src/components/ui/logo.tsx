interface LogoProps {
  showText?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

export function Logo({ showText = true, size = 'md' }: LogoProps) {
  const sizeClasses = {
    sm: 'w-9 h-9',
    md: 'w-12 h-12',
    lg: 'w-16 h-16',
  };

  const textSize = {
    sm: 'text-base',
    md: 'text-lg',
    lg: 'text-xl',
  };

  return (
    <div className="flex items-center gap-2">
      <img
        src={`${import.meta.env.BASE_URL}logo.png`}
        alt="TRADEX Logo"
        className={`${sizeClasses[size]} shrink-0 object-contain`}
      />
      {showText && (
        <span className={`text-white font-bold ${textSize[size]}`}>
          TRADEX
        </span>
      )}
    </div>
  );
}
