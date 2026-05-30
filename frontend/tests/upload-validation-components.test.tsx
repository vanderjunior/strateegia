import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/config", () => ({
  getApiConfig: vi.fn()
}));

vi.mock("@/lib/api/documents", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/documents")>("@/lib/api/documents");
  return {
    ...actual,
    uploadMaterialFile: vi.fn()
  };
});

vi.mock("@/lib/adapters/session", () => ({
  buildDefaultSessionState: vi.fn(() => ({
    status: "authenticated",
    label: "Sessão ativa",
    description: "Você está conectado.",
    source: "backend",
    userLabel: "Usuário interno"
  })),
  loadSessionState: vi.fn(async () => ({
    status: "authenticated",
    label: "Sessão ativa",
    description: "Você está conectado.",
    source: "backend",
    userLabel: "Usuário interno"
  }))
}));

import { MaterialUploadEntryClient } from "@/components/workspace/MaterialUploadEntryClient";
import {
  acceptedUploadTypes,
  extensionForFileName,
  formatUploadFileSize,
  validateUploadFile
} from "@/components/workspace/upload-validation";
import { getApiConfig } from "@/lib/api/config";
import { uploadMaterialFile } from "@/lib/api/documents";
import { loadSessionState } from "@/lib/adapters/session";

function makeFile(name: string, type: string, size = 1024): File {
  const file = new File(["demo"], name, { type });
  Object.defineProperty(file, "size", { value: size });
  return file;
}

describe("upload validation helpers and component states", () => {
  beforeEach(() => {
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "http://127.0.0.1:8000",
      forceMock: false
    });
  });

  it("accepts valid pdf, txt, and md files", () => {
    expect(validateUploadFile(makeFile("material.pdf", "application/pdf")).valid).toBe(true);
    expect(validateUploadFile(makeFile("material.txt", "text/plain")).valid).toBe(true);
    expect(validateUploadFile(makeFile("material.md", "text/markdown")).valid).toBe(true);
    expect(extensionForFileName("material.md")).toBe(".md");
    expect(formatUploadFileSize(1024)).toBe("1 KB");
  });

  it("rejects oversized files and unsupported extensions", () => {
    expect(validateUploadFile(makeFile("material.exe", "application/octet-stream")).message).toBe(
      "Tipo de arquivo não suportado."
    );
    expect(validateUploadFile(makeFile("material.pdf", "application/pdf", 6 * 1024 * 1024)).message).toBe(
      "O arquivo excede o limite atual de 5 MB."
    );
  });

  it("keeps .markdown out of the accepted backend extension list", () => {
    const serialized = JSON.stringify(acceptedUploadTypes);
    expect(serialized).not.toContain(".markdown");
  });

  it("requires a valid file, intent, and confirmation before enabling send", async () => {
    const { container } = render(<MaterialUploadEntryClient />);
    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
    const checkbox = screen.getByRole("checkbox");
    const editalIntent = screen.getByRole("radio", { name: "Edital" });
    const button = screen.getByRole("button", { name: "Enviar arquivo" });

    expect(button).toBeDisabled();
    expect(screen.getAllByText(/OCR em validação/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/PDFs escaneados podem exigir OCR/i).length).toBeGreaterThan(0);
    expect(screen.getByText("O que você está enviando?")).toBeInTheDocument();
    expect(screen.getByText("Material de estudo")).toBeInTheDocument();
    expect(screen.getByText("Prova anterior")).toBeInTheDocument();
    expect(screen.getByText("Bibliografia / referência")).toBeInTheDocument();
    expect(screen.getByText("Confirmo que este material pode ser enviado para validação.")).toBeInTheDocument();

    fireEvent.change(fileInput, {
      target: {
        files: [makeFile("material.pdf", "application/pdf")]
      }
    });

    await waitFor(() => {
      expect(screen.getAllByText("Arquivo pronto para validação.").length).toBeGreaterThan(0);
    });
    expect(button).toBeDisabled();

    fireEvent.click(checkbox);
    expect(button).toBeDisabled();
    expect(screen.getAllByText("Classificação necessária.").length).toBeGreaterThan(0);

    fireEvent.click(editalIntent);
    expect(button).toBeEnabled();
  });

  it("shows a friendly invalid message for unsupported files", () => {
    const { container } = render(<MaterialUploadEntryClient />);
    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;

    fireEvent.change(fileInput, {
      target: {
        files: [makeFile("material.exe", "application/octet-stream")]
      }
    });

    expect(screen.getAllByText("Tipo de arquivo não suportado.").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Enviar arquivo" })).toBeDisabled();
  });

  it("shows the selected classification after a successful upload without claiming backend processing uses it", async () => {
    vi.mocked(uploadMaterialFile).mockResolvedValueOnce({
      ok: true,
      data: {
        documentId: "doc-123",
        filename: "edital.pdf",
        originalFilename: "edital.pdf",
        contentType: "application/pdf",
        materialType: "edital",
        materialTypeLabel: "Edital",
        sizeBytes: 2048,
        processingStatus: "Material recebido para validação",
        extractionStatus: "Texto extraído",
        reviewState: "Pronto para revisão",
        source: "backend",
        demoOnly: false
      },
      status: 201,
      source: "backend"
    });

    const { container } = render(<MaterialUploadEntryClient />);
    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;

    fireEvent.change(fileInput, {
      target: {
        files: [makeFile("edital.pdf", "application/pdf", 2048)]
      }
    });
    fireEvent.click(screen.getByRole("radio", { name: "Edital" }));
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: "Enviar arquivo" }));

    expect((await screen.findAllByText("Material recebido para validação")).length).toBeGreaterThan(0);
    expect(screen.getByText("classificação escolhida")).toBeInTheDocument();
    expect(screen.getAllByText("Edital").length).toBeGreaterThan(0);
    expect(screen.getByText(/não aciona processamento automático/i)).toBeInTheDocument();
  });

  it("blocks the upload form and shows login CTA when there is no active session", async () => {
    vi.mocked(loadSessionState).mockResolvedValueOnce({
      status: "unauthenticated",
      label: "Entrar para continuar",
      description: "Entre para acessar seus materiais.",
      source: "backend"
    });

    render(<MaterialUploadEntryClient />);

    expect(await screen.findByText("Entre para enviar materiais.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Entrar" })).toHaveAttribute("href", "/login");
    expect(screen.queryByLabelText(/Escolha um arquivo/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Enviar arquivo" })).not.toBeInTheDocument();
  });
});
