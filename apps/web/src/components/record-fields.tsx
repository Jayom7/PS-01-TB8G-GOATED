"use client";

// Edit only keys already present in the record. The API owns the table schema.
export function RecordFields({ json, onChange, disabled }: { json: string; onChange: (value: string) => void; disabled: boolean }) {
  let fields: Record<string, unknown>;
  try {
    const parsed: unknown = JSON.parse(json);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error();
    fields = parsed as Record<string, unknown>;
  } catch {
    return <p className="field-hint" role="status">Use the JSON editor below to correct this record. Your input has been retained.</p>;
  }
  const update = (key: string, value: unknown) => onChange(JSON.stringify({ ...fields, [key]: value }, null, 2));
  return <div className="record-fields">{Object.entries(fields).map(([key, value]) => {
    const label = key.replaceAll("_", " ");
    if (value !== null && typeof value === "object") return <p className="field-hint" key={key}>“{label}” must be a scalar value. Correct it in the JSON editor.</p>;
    const date = (typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value)) || ((value === null || value === "") && /(_date|_on|_as_of)$/.test(key));
    const numeric = typeof value === "number" || key.endsWith("_minor_units");
    return <label className="field-label" key={key}><span>{label}</span>{typeof value === "boolean" ? <select disabled={disabled} value={String(value)} onChange={(event) => update(key, event.target.value === "true")}><option value="true">True</option><option value="false">False</option></select> : <input disabled={disabled} type={numeric ? "number" : date ? "date" : "text"} step={key.endsWith("_minor_units") ? "1" : "any"} value={value === null ? "" : String(value)} placeholder={value === null ? "Not set (null)" : undefined} onChange={(event) => update(key, numeric ? event.target.value === "" ? null : Number(event.target.value) : event.target.value || (value === null ? null : ""))} />}{key.endsWith("_minor_units") && <small className="field-hint">Minor currency units · 100 = 1.00</small>}</label>;
  })}</div>;
}
