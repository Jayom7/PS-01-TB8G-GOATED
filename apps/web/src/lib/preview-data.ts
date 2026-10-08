export const sampleQuestion =
  "What is Acme's overdue amount and what payment terms does its contract specify?";

export const previewAnswer = [
  {
    text: "Acme has an overdue amount of USD 48,000 on invoice INV-2048. It was due on December 15, 2024, and remained unpaid on January 10, 2025.",
    citations: ["invoice-2048"],
  },
  {
    text: "The agreement specifies Net 30 payment terms from the invoice date, payable by bank transfer.",
    citations: ["acme-contract-page-8"],
  },
];

export const previewSources = [
  {
    id: "invoice-2048",
    number: "1",
    title: "Invoice INV-2048",
    location: "Row 17 · Accounts receivable",
    type: "Structured record",
    detail: "INV-2048  ·  Acme  ·  USD 48,000  ·  Due Dec 15, 2024  ·  Unpaid",
  },
  {
    id: "acme-contract-page-8",
    number: "2",
    title: "Acme Services Agreement",
    location: "Page 8 · Section 4.2 Payment Terms",
    type: "PDF page",
    detail:
      "Invoices are due Net 30 from the invoice date. Amounts are due in USD and payable by bank transfer.",
  },
] as const;

export const previewRoles = [
  "CEO",
  "Finance Manager",
  "HR Manager",
  "Sales Manager",
  "Engineer",
] as const;

export type PreviewRole = (typeof previewRoles)[number];
export type WorkspaceView = "Chat" | "Sources" | "Ingestion" | "Evaluation";
