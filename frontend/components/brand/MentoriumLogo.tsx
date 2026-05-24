export function MentoriumLogo({ compact = false }: { compact?: boolean }) {
  return (
    <div className="inline-flex items-center gap-3">
      <svg
        aria-hidden="true"
        className={compact ? "h-10 w-10" : "h-12 w-12"}
        viewBox="0 0 96 96"
        fill="none"
      >
        <circle cx="48" cy="48" r="35" stroke="rgba(201,169,110,0.55)" strokeWidth="1.6" />
        <circle cx="48" cy="48" r="22" stroke="rgba(168,184,196,0.28)" strokeWidth="1.2" />
        <path d="M48 12V84M12 48H84M24 24L72 72M72 24L24 72" stroke="rgba(168,184,196,0.18)" strokeWidth="1" />
        <path d="M48 18L56 40L78 48L56 56L48 78L40 56L18 48L40 40L48 18Z" fill="rgba(201,169,110,0.18)" stroke="#c9a96e" strokeWidth="1.8" />
        <circle cx="48" cy="48" r="6" fill="#dfc08a" />
        <circle cx="24" cy="48" r="3.2" fill="#a8b8c4" />
        <circle cx="72" cy="48" r="3.2" fill="#a8b8c4" />
        <circle cx="48" cy="24" r="3.2" fill="#a8b8c4" />
        <circle cx="48" cy="72" r="3.2" fill="#a8b8c4" />
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
