"use client";

import { useCallback, useState } from "react";
import DashboardNavbar from "@/components/dashboard-navbar";
import { chunkText } from "@/lib/chunk";
import { useDropzone } from "react-dropzone";

type ParsedFile = {
  name: string;
  type: string;
  text: string;
  chunks: string[];
};

const CHUNK_SIZE = 1200;
const CHUNK_OVERLAP = 200;
const DROP_ACCEPT = {
  "application/pdf": [".pdf"],
  "text/plain": [".txt"],
  "text/markdown": [".md", ".markdown"],
} as const;

export default function ImportPage() {
  const [parsedFiles, setParsedFiles] = useState<ParsedFile[]>([]);
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (!acceptedFiles || acceptedFiles.length === 0) return;
    setError(null);

    const results: ParsedFile[] = [];
    for (const file of acceptedFiles) {
      const type = file.type || inferMimeFromName(file.name);
      try {
        let text = "";
        if (type === "text/plain" || file.name.toLowerCase().endsWith(".txt")) {
          text = await file.text();
        } else if (
          type === "application/pdf" ||
          file.name.toLowerCase().endsWith(".pdf")
        ) {
          text = await extractPdfTextBrowser(file);
        } else if (
          type === "text/markdown" ||
          file.name.toLowerCase().endsWith(".md")
        ) {
          text = await file.text();
        } else {
          throw new Error(`Unsupported file type: ${type || "unknown"}`);
        }

        const chunks = chunkText(text, {
          size: CHUNK_SIZE,
          overlap: CHUNK_OVERLAP,
        });
        results.push({ name: file.name, type, text, chunks });
      } catch (e: any) {
        console.error("Import error for file:", file.name, e);
        setError(`${file.name}: ${e?.message || "Failed to parse file"}`);
      }
    }

    setParsedFiles(results);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: true,
    accept: DROP_ACCEPT,
  });

  return (
    <div className="min-h-screen bg-white">
      <DashboardNavbar />
      <main className="container mx-auto px-4 pt-28 pb-16">
        <h1 className="text-3xl font-bold text-black mb-6">Import Documents</h1>
        <p className="text-black mb-6">
          Drop PDF, TXT, or MD files below. We will extract text, chunk it, and
          show the chunks on screen.
        </p>

        <div
          className={`border-2 border-dashed rounded-xl p-10 text-center transition-colors ${isDragActive ? "border-blue-400 bg-blue-50" : "border-gray-300 bg-white"}`}
          {...getRootProps()}
        >
          <input {...getInputProps()} />
          <div className="text-black">
            {isDragActive
              ? "Drop the files here..."
              : "Click to select files or drag and drop here"}
          </div>
          <div className="text-xs text-black mt-2">Supported: PDF, TXT, MD</div>
        </div>

        {error && (
          <div className="mt-6 text-red-500 bg-red-100 border border-red-700/50 p-4 rounded-lg text-black">
            {error}
          </div>
        )}

        {parsedFiles.length > 0 && (
          <section className="mt-10 space-y-8">
            {parsedFiles.map((pf) => (
              <div
                key={pf.name}
                className="bg-gray-100 border border-gray-200 rounded-xl p-6"
              >
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-semibold text-black">
                    {pf.name}
                  </h2>
                  <span className="text-xs text-black">
                    {pf.chunks.length} chunks
                  </span>
                </div>
                <div className="text-xs text-black mb-3">{pf.type}</div>
                <div className="grid gap-4">
                  {pf.chunks.map((chunk, idx) => (
                    <div
                      key={idx}
                      className="bg-gray-200 border border-gray-300 rounded-lg p-4"
                    >
                      <div className="text-xs text-black mb-2">
                        Chunk {idx + 1}
                      </div>
                      <pre className="whitespace-pre-wrap text-sm text-black">
                        {chunk}
                      </pre>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </section>
        )}
      </main>
    </div>
  );
}

function inferMimeFromName(name: string): string {
  const lower = name.toLowerCase();
  if (lower.endsWith(".pdf")) return "application/pdf";
  if (lower.endsWith(".txt")) return "text/plain";
  if (lower.endsWith(".md") || lower.endsWith(".markdown"))
    return "text/markdown";
  return "";
}

async function extractPdfTextBrowser(file: File): Promise<string> {
  try {
    const arrayBuffer = await file.arrayBuffer();
    const pdfjs: any = await import("pdfjs-dist");
    const { getDocument, GlobalWorkerOptions, VerbosityLevel } = pdfjs as any;

    // Create worker and attach diagnostics
    const worker = new Worker("/pdf.worker.mjs?v=1", { type: "module" } as any);
    worker.addEventListener("error", (ev: any) => {
      console.error("PDF worker error:", ev?.message || ev, ev?.error);
    });
    worker.addEventListener("messageerror", (ev: any) => {
      console.error("PDF worker messageerror:", ev);
    });
    (GlobalWorkerOptions as any).workerPort = worker;

    // Increase verbosity to get console output from pdfjs if needed
    if (VerbosityLevel) {
      (pdfjs as any).verbosity = VerbosityLevel.errors;
    }

    const loadingTask = getDocument({ data: arrayBuffer });
    loadingTask.onPassword = (cb: any) => cb(null); // in case of password-protected PDFs
    const pdf = await loadingTask.promise;

    let fullText = "";
    for (let i = 1; i <= pdf.numPages; i++) {
      const page = await pdf.getPage(i);
      const content = await page.getTextContent();
      const strings = content.items
        .map((it: any) => ("str" in it ? it.str : ""))
        .filter(Boolean);
      fullText += strings.join(" ") + "\n";
    }

    try {
      worker.terminate();
    } catch {}
    return fullText;
  } catch (err: any) {
    console.error("PDF parse fatal error:", err);
    throw err;
  }
}
