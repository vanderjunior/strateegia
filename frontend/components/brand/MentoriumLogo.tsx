import { useId } from "react";

export function MentoriumLogo({ compact = false }: { compact?: boolean }) {
  const gradientId = useId();

  return (
    <div className="inline-flex items-center gap-3">
      <svg
        role="img"
        aria-label="Mentorium logo"
        className={compact ? "h-10 w-10" : "h-12 w-12"}
        viewBox="0 0 100 100"
        fill="none"
      >
        <circle cx="50" cy="50" r="44" stroke="rgba(168,184,196,0.18)" strokeWidth="1" strokeDasharray="3 3" />
        <circle cx="50" cy="50" r="32" stroke="rgba(201,169,110,0.28)" strokeWidth="1" opacity="0.4" />
        <line x1="50" y1="12" x2="50" y2="88" stroke="rgba(168,184,196,0.18)" strokeWidth="1" />
        <line x1="12" y1="50" x2="88" y2="50" stroke="rgba(168,184,196,0.18)" strokeWidth="1" />
        <path d="M50 15L53.5 50L50 85L46.5 50Z" fill="#2a4a61" opacity="0.3" />
        <path d="M50 15L50 50L46.5 50Z" fill="#a8b8c4" opacity="0.2" />
        <path d="M50 8L54 18L46 18Z" fill="#c9a96e" />
        <path
          d="M28 68L28 30L50 54L72 30L72 68"
          stroke={`url(#${gradientId})`}
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <line x1="28" y1="30" x2="50" y2="18" stroke="#a8b8c4" strokeWidth="1.2" strokeDasharray="2 2" opacity="0.6" />
        <line x1="72" y1="30" x2="50" y2="18" stroke="#a8b8c4" strokeWidth="1.2" strokeDasharray="2 2" opacity="0.6" />
        <circle cx="50" cy="18" r="3.5" fill="#c9a96e" />
        <circle cx="28" cy="68" r="4.5" fill="#a8b8c4" stroke="#0f1e2a" strokeWidth="1.5" />
        <circle cx="28" cy="30" r="5" fill="#dfc08a" stroke="#0f1e2a" strokeWidth="1.5" />
        <circle cx="50" cy="54" r="6" fill="#c9a96e" stroke="#0f1e2a" strokeWidth="1.5" />
        <circle cx="72" cy="30" r="5" fill="#dfc08a" stroke="#0f1e2a" strokeWidth="1.5" />
        <circle cx="72" cy="68" r="4.5" fill="#a8b8c4" stroke="#0f1e2a" strokeWidth="1.5" />
        <defs>
          <linearGradient id={gradientId} x1="28" y1="30" x2="72" y2="68" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#dfc08a" />
            <stop offset="50%" stopColor="#c9a96e" />
            <stop offset="100%" stopColor="#dfc08a" />
          </linearGradient>
        </defs>
      </svg>
      <div>
        <div className="font-serif text-3xl leading-none text-ink">Mentorium</div>
        <div className="font-mono text-[11px] uppercase tracking-[0.24em] text-silver">
          edital-aware technical study
        </div>
      </div>
    </div>
  );
}
