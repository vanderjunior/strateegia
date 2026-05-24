export function Progress({
  value
}: {
  value: number;
}) {
  return (
    <div className="h-2 overflow-hidden rounded-full bg-[rgba(168,184,196,0.12)]">
      <div
        className="h-full rounded-full bg-gradient-to-r from-gold to-[#dfc08a]"
        style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
      />
    </div>
  );
}
