export function LiquidGlassFilterDefs() {
  return (
    <svg className="liquid-glass-filter-defs" aria-hidden="true" focusable="false">
      <filter id="lg-sidebar-distortion" x="-20%" y="-20%" width="140%" height="140%" colorInterpolationFilters="sRGB">
        <feTurbulence type="fractalNoise" baseFrequency="0.012 0.018" numOctaves={2} seed={92} result="noise" />
        <feGaussianBlur in="noise" stdDeviation="1.6" result="blurredNoise" />
        <feDisplacementMap in="SourceGraphic" in2="blurredNoise" scale={18} xChannelSelector="R" yChannelSelector="G" />
      </filter>
    </svg>
  );
}
