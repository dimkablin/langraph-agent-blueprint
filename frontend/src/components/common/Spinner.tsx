export function Spinner({ size = "icon" }: { size?: "dot" | "icon" }) {
  const className = size === "dot" ? "spinner spinner-dot" : "spinner spinner-icon";
  return <span className={className} aria-hidden="true" />;
}

