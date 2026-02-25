// --- TonbilAiFirewall V2.0 Logo Component ---
// Neon cyberpunk temali kalkan + AI devre + firewall duvarı

interface FirewallLogoProps {
  size?: number;
  className?: string;
}

export function FirewallLogo({ size = 40, className = "" }: FirewallLogoProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 512 512"
      width={size}
      height={size}
      className={className}
    >
      <defs>
        <filter id="glowC" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur in="SourceGraphic" stdDeviation="8" result="blur"/>
          <feColorMatrix in="blur" type="matrix" values="0 0 0 0 0  0 0.94 1 0 0  0 0 1 0 0  0 0 0 0.6 0" result="glow"/>
          <feMerge><feMergeNode in="glow"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
        <filter id="glowM" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur in="SourceGraphic" stdDeviation="6" result="blur"/>
          <feColorMatrix in="blur" type="matrix" values="1 0 0 0 0  0 0 0 0 0  0 0 0.9 0 0  0 0 0 0.5 0" result="glow"/>
          <feMerge><feMergeNode in="glow"/><feMergeNode in="SourceGraphic"/></feMerge>
        </filter>
        <linearGradient id="sGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style={{stopColor:"#00F0FF",stopOpacity:0.15}}/>
          <stop offset="50%" style={{stopColor:"#0A0A0F",stopOpacity:0.9}}/>
          <stop offset="100%" style={{stopColor:"#FF00E5",stopOpacity:0.1}}/>
        </linearGradient>
        <linearGradient id="bGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style={{stopColor:"#00F0FF",stopOpacity:1}}/>
          <stop offset="50%" style={{stopColor:"#00F0FF",stopOpacity:0.4}}/>
          <stop offset="100%" style={{stopColor:"#FF00E5",stopOpacity:0.8}}/>
        </linearGradient>
        <linearGradient id="cGrad" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" style={{stopColor:"#00F0FF",stopOpacity:1}}/>
          <stop offset="100%" style={{stopColor:"#00F0FF",stopOpacity:0.3}}/>
        </linearGradient>
      </defs>

      {/* Shield body */}
      <path d="M256 28 L462 120 C462 120 472 300 256 484 C40 300 50 120 50 120 Z"
            fill="url(#sGrad)" stroke="url(#bGrad)" strokeWidth="6" filter="url(#glowC)"/>
      {/* Inner shield */}
      <path d="M256 62 L430 140 C430 140 438 290 256 450 C74 290 82 140 82 140 Z"
            fill="none" stroke="#00F0FF" strokeWidth="1.5" opacity="0.25"/>

      {/* Firewall bricks */}
      <line x1="130" y1="190" x2="382" y2="190" stroke="#00F0FF" strokeWidth="2" opacity="0.3"/>
      <line x1="120" y1="240" x2="392" y2="240" stroke="#00F0FF" strokeWidth="2" opacity="0.25"/>
      <line x1="130" y1="290" x2="382" y2="290" stroke="#00F0FF" strokeWidth="2" opacity="0.2"/>
      <line x1="150" y1="340" x2="362" y2="340" stroke="#00F0FF" strokeWidth="2" opacity="0.15"/>
      <line x1="220" y1="190" x2="220" y2="240" stroke="#00F0FF" strokeWidth="1.5" opacity="0.2"/>
      <line x1="310" y1="190" x2="310" y2="240" stroke="#00F0FF" strokeWidth="1.5" opacity="0.2"/>
      <line x1="180" y1="240" x2="180" y2="290" stroke="#00F0FF" strokeWidth="1.5" opacity="0.2"/>
      <line x1="265" y1="240" x2="265" y2="290" stroke="#00F0FF" strokeWidth="1.5" opacity="0.2"/>
      <line x1="345" y1="240" x2="345" y2="290" stroke="#00F0FF" strokeWidth="1.5" opacity="0.2"/>

      {/* AI eye core */}
      <circle cx="256" cy="230" r="52" fill="none" stroke="#00F0FF" strokeWidth="3" filter="url(#glowC)" opacity="0.9"/>
      <circle cx="256" cy="230" r="36" fill="none" stroke="#FF00E5" strokeWidth="2" filter="url(#glowM)" opacity="0.7"/>
      <circle cx="256" cy="230" r="18" fill="#00F0FF" opacity="0.8" filter="url(#glowC)"/>
      <circle cx="256" cy="230" r="8" fill="#ffffff" opacity="0.9"/>

      {/* Circuit nodes */}
      <line x1="256" y1="178" x2="256" y2="155" stroke="url(#cGrad)" strokeWidth="2"/>
      <circle cx="256" cy="152" r="4" fill="#00F0FF" opacity="0.8"/>
      <line x1="256" y1="282" x2="256" y2="310" stroke="url(#cGrad)" strokeWidth="2"/>
      <circle cx="256" cy="313" r="4" fill="#00F0FF" opacity="0.8"/>
      <line x1="204" y1="230" x2="175" y2="230" stroke="url(#cGrad)" strokeWidth="2"/>
      <circle cx="172" cy="230" r="4" fill="#00F0FF" opacity="0.8"/>
      <line x1="308" y1="230" x2="337" y2="230" stroke="url(#cGrad)" strokeWidth="2"/>
      <circle cx="340" cy="230" r="4" fill="#00F0FF" opacity="0.8"/>
      {/* Diagonal nodes */}
      <line x1="219" y1="193" x2="200" y2="174" stroke="#00F0FF" strokeWidth="1.5" opacity="0.5"/>
      <circle cx="197" cy="171" r="3" fill="#FF00E5" opacity="0.6"/>
      <line x1="293" y1="193" x2="312" y2="174" stroke="#00F0FF" strokeWidth="1.5" opacity="0.5"/>
      <circle cx="315" cy="171" r="3" fill="#FF00E5" opacity="0.6"/>
      <line x1="219" y1="267" x2="200" y2="286" stroke="#00F0FF" strokeWidth="1.5" opacity="0.5"/>
      <circle cx="197" cy="289" r="3" fill="#FF00E5" opacity="0.6"/>
      <line x1="293" y1="267" x2="312" y2="286" stroke="#00F0FF" strokeWidth="1.5" opacity="0.5"/>
      <circle cx="315" cy="289" r="3" fill="#FF00E5" opacity="0.6"/>

      {/* Lock keyhole */}
      <rect x="248" y="360" width="16" height="20" rx="3" fill="#00F0FF" opacity="0.5"/>
      <circle cx="256" cy="358" r="12" fill="none" stroke="#00F0FF" strokeWidth="2.5" opacity="0.5"/>
    </svg>
  );
}
