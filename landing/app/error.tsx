"use client";

export default function Error({
  error,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div
      style={{
        background: "#080810",
        color: "#ff3344",
        padding: "2rem",
        fontFamily: "monospace",
        whiteSpace: "pre-wrap",
        minHeight: "100vh",
      }}
    >
      <h2 style={{ marginBottom: "1rem" }}>Debug: Caught Error</h2>
      <p>
        <strong>Message:</strong> {error.message}
      </p>
      <p>
        <strong>Name:</strong> {error.name}
      </p>
      <p>
        <strong>Digest:</strong> {error.digest || "none"}
      </p>
      <p style={{ marginTop: "1rem", color: "#ffaa22" }}>
        <strong>Stack:</strong>
        {"\n"}
        {error.stack}
      </p>
    </div>
  );
}
