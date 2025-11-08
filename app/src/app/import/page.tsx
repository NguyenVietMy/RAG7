"use client";

import { useCallback, useState, useEffect } from "react";
import DashboardNavbar from "@/components/dashboard-navbar";
import { chunkText } from "@/lib/chunk";
import { useDropzone } from "react-dropzone";
import { apiClient } from "@/lib/api-client";
import { createClient } from "../../../supabase/client";

type ParsedFile = {
  name: string;
  type: string;
  text: string;
  chunks: string[];
};

type UploadStatus = {
  status: "idle" | "uploading" | "success" | "error";
  progress: number; // 0-100
  error?: string;
  chunksUploaded?: number;
  totalChunks?: number;
};

const CHUNK_SIZE = 1200;
const CHUNK_OVERLAP = 200;
const DROP_ACCEPT = {
  "application/pdf": [".pdf"],
  "text/plain": [".txt"],
  "text/markdown": [".md", ".markdown"],
} as const;

type Collection = {
  name: string;
  metadata?: Record<string, any>;
  count?: number;
};

export default function ImportPage() {
  const [parsedFiles, setParsedFiles] = useState<ParsedFile[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [collectionName, setCollectionName] = useState<string>("");
  const [collections, setCollections] = useState<Collection[]>([]);
  const [isLoadingCollections, setIsLoadingCollections] =
    useState<boolean>(true);
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [newProfessionalName, setNewProfessionalName] = useState<string>("");
  const [newProfessionalDescription, setNewProfessionalDescription] =
    useState<string>("");
  const [isCreating, setIsCreating] = useState<boolean>(false);
  const [uploadStatuses, setUploadStatuses] = useState<
    Map<string, UploadStatus>
  >(new Map());
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [uploadedFiles, setUploadedFiles] = useState<Set<string>>(new Set());

  // Fetch collections on mount
  useEffect(() => {
    loadCollections();
  }, []);

  const loadCollections = useCallback(async () => {
    setIsLoadingCollections(true);
    try {
      const response = await apiClient.listCollections();
      setCollections(response.collections || []);
    } catch (err: any) {
      console.error("Failed to load collections:", err);
      setError(
        `Failed to load collections: ${err?.message || "Unknown error"}`
      );
    } finally {
      setIsLoadingCollections(false);
    }
  }, []);

  const handleCreateProfessional = useCallback(async () => {
    if (!newProfessionalName.trim()) {
      setError("Please enter a professional name");
      return;
    }

    setIsCreating(true);
    setError(null);

    try {
      const supabase = createClient();
      const {
        data: { user },
      } = await supabase.auth.getUser();

      if (!user) {
        throw new Error("You must be logged in to create a professional");
      }

      // Sanitize collection name (lowercase, replace spaces with underscores)
      const sanitizedCollectionName = newProfessionalName
        .toLowerCase()
        .replace(/\s+/g, "_")
        .replace(/[^a-z0-9_]/g, "");

      if (!sanitizedCollectionName) {
        throw new Error("Invalid professional name");
      }

      // Create collection in ChromaDB first
      await apiClient.createCollection(sanitizedCollectionName);

      // Insert professional record in database
      const { error: dbError } = await supabase.from("professionals").insert({
        user_id: user.id,
        collection_name: sanitizedCollectionName,
        name: newProfessionalName,
        description: newProfessionalDescription || null,
      });

      if (dbError) {
        throw new Error(`Failed to create professional: ${dbError.message}`);
      }

      // Reload collections
      await loadCollections();

      // Select the newly created collection
      setCollectionName(sanitizedCollectionName);

      // Close modal and reset form
      setShowCreateModal(false);
      setNewProfessionalName("");
      setNewProfessionalDescription("");
      setSuccessMessage(
        `Professional "${newProfessionalName}" created successfully!`
      );
    } catch (err: any) {
      console.error("Create professional error:", err);
      setError(err?.message || "Failed to create professional");
    } finally {
      setIsCreating(false);
    }
  }, [newProfessionalName, newProfessionalDescription, loadCollections]);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      if (!acceptedFiles || acceptedFiles.length === 0) return;
      setError(null);

      const results: ParsedFile[] = [];
      const skippedFiles: string[] = [];

      for (const file of acceptedFiles) {
        // Check if file is already uploaded
        if (uploadedFiles.has(file.name)) {
          skippedFiles.push(file.name);
          continue;
        }

        const type = file.type || inferMimeFromName(file.name);
        try {
          let text = "";
          if (
            type === "text/plain" ||
            file.name.toLowerCase().endsWith(".txt")
          ) {
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

      if (skippedFiles.length > 0) {
        setError(
          `These files are already uploaded and were skipped: ${skippedFiles.join(", ")}`
        );
      }

      if (results.length > 0) {
        setParsedFiles((prev) => [...prev, ...results]);
        // Reset upload statuses for new files
        setUploadStatuses((prev) => {
          const next = new Map(prev);
          results.forEach((file) => {
            next.set(file.name, { status: "idle", progress: 0 });
          });
          return next;
        });
        setSuccessMessage(null);
      }
    },
    [uploadedFiles]
  );

  const generateChunkId = (fileName: string, chunkIndex: number): string => {
    const sanitized = fileName.replace(/[^a-zA-Z0-9]/g, "_");
    const timestamp = Date.now();
    return `${sanitized}_chunk_${chunkIndex}_${timestamp}`;
  };

  const handleUpload = useCallback(async () => {
    if (!collectionName.trim()) {
      setError("Please enter a collection name");
      return;
    }

    // Filter out already uploaded files
    const filesToUpload = parsedFiles.filter(
      (file) => !uploadedFiles.has(file.name)
    );

    if (filesToUpload.length === 0) {
      setError("All files have already been uploaded");
      return;
    }

    setError(null);
    setSuccessMessage(null);
    setIsUploading(true);

    let totalUploaded = 0;
    let totalChunks = 0;

    // Count total chunks for files that will be uploaded
    filesToUpload.forEach((file) => {
      totalChunks += file.chunks.length;
    });

    try {
      // Process each file sequentially
      for (const file of filesToUpload) {
        // Skip if already uploaded
        if (uploadedFiles.has(file.name)) {
          continue;
        }

        if (file.chunks.length === 0) {
          setUploadStatuses((prev) => {
            const next = new Map(prev);
            next.set(file.name, {
              status: "error",
              progress: 0,
              error: "No chunks to upload",
            });
            return next;
          });
          continue;
        }

        // Update status to uploading
        setUploadStatuses((prev) => {
          const next = new Map(prev);
          next.set(file.name, {
            status: "uploading",
            progress: 10, // Show initial progress
            totalChunks: file.chunks.length,
            chunksUploaded: 0,
          });
          return next;
        });

        try {
          // Generate IDs and metadata for all chunks
          const ids = file.chunks.map((_, idx) =>
            generateChunkId(file.name, idx)
          );
          const documents = file.chunks;
          const metadatas = file.chunks.map((_, idx) => ({
            filename: file.name,
            file_type: file.type,
            chunk_index: idx,
            uploaded_at: new Date().toISOString(),
          }));

          // Update progress to show activity
          setUploadStatuses((prev) => {
            const next = new Map(prev);
            next.set(file.name, {
              status: "uploading",
              progress: 50, // Show progress during API call
              totalChunks: file.chunks.length,
              chunksUploaded: 0,
            });
            return next;
          });

          // Call API to upsert (backend will handle embedding)
          await apiClient.upsert(collectionName, {
            ids,
            documents,
            metadatas,
          });

          // Update status to success
          setUploadStatuses((prev) => {
            const next = new Map(prev);
            next.set(file.name, {
              status: "success",
              progress: 100,
              totalChunks: file.chunks.length,
              chunksUploaded: file.chunks.length,
            });
            return next;
          });

          // Mark file as uploaded to prevent re-upload
          setUploadedFiles((prev) => {
            const next = new Set(prev);
            next.add(file.name);
            return next;
          });

          totalUploaded += file.chunks.length;
        } catch (uploadError: any) {
          console.error("Upload error for file:", file.name, uploadError);
          setUploadStatuses((prev) => {
            const next = new Map(prev);
            next.set(file.name, {
              status: "error",
              progress: 0,
              error: uploadError?.message || "Failed to upload",
            });
            return next;
          });
        }
      }

      if (totalUploaded > 0) {
        setSuccessMessage(
          `Successfully uploaded ${totalUploaded} chunks from ${filesToUpload.length} file(s) to collection "${collectionName}"`
        );
      }
    } catch (err: any) {
      console.error("Upload process error:", err);
      setError(err?.message || "An error occurred during upload");
    } finally {
      setIsUploading(false);
    }
  }, [collectionName, parsedFiles, uploadedFiles]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: true,
    accept: DROP_ACCEPT,
    disabled: isUploading,
  });

  // Check if all files are uploaded
  const allFilesUploaded =
    parsedFiles.length > 0 &&
    parsedFiles.every((file) => uploadedFiles.has(file.name));

  return (
    <div className="min-h-screen bg-white">
      <DashboardNavbar />
      <main className="container mx-auto px-4 pt-28 pb-16">
        <h1 className="text-3xl font-bold text-black mb-6">Import Documents</h1>
        <p className="text-black mb-6">
          Drop PDF, TXT, or MD files below. We will extract text, chunk it, and
          upload to ChromaDB.
        </p>

        {/* Collection Dropdown */}
        <div className="mb-6">
          <label
            htmlFor="collection-select"
            className="block text-sm font-medium text-black mb-2"
          >
            Collection / Professional
          </label>
          <div className="flex gap-2">
            <select
              id="collection-select"
              value={collectionName}
              onChange={(e) => {
                if (e.target.value === "__create__") {
                  setShowCreateModal(true);
                  // Reset select to previous value
                  e.target.value = collectionName;
                } else {
                  setCollectionName(e.target.value);
                }
              }}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-black bg-white"
              disabled={isUploading || isLoadingCollections}
            >
              <option value="">
                {isLoadingCollections
                  ? "Loading..."
                  : "Select a professional..."}
              </option>
              {collections.map((col) => (
                <option key={col.name} value={col.name}>
                  {col.name}{" "}
                  {col.count !== null && col.count !== undefined
                    ? `(${col.count} docs)`
                    : ""}
                </option>
              ))}
              <option value="__create__" className="font-semibold">
                + Create New Professional
              </option>
            </select>
          </div>
          <p className="text-xs text-gray-600 mt-1">
            Select an existing professional or create a new one
          </p>
        </div>

        {/* Create Professional Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
              <h2 className="text-xl font-bold text-black mb-4">
                Create New Professional
              </h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-black mb-2">
                    Professional Name *
                  </label>
                  <input
                    type="text"
                    value={newProfessionalName}
                    onChange={(e) => setNewProfessionalName(e.target.value)}
                    placeholder="e.g., Data Science Advisor"
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-black bg-white"
                    disabled={isCreating}
                    autoFocus
                    onKeyDown={(e) => {
                      if (
                        e.key === "Enter" &&
                        !isCreating &&
                        newProfessionalName.trim()
                      ) {
                        handleCreateProfessional();
                      }
                    }}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-black mb-2">
                    Description (Optional)
                  </label>
                  <textarea
                    value={newProfessionalDescription}
                    onChange={(e) =>
                      setNewProfessionalDescription(e.target.value)
                    }
                    placeholder="Brief description of what this professional does..."
                    rows={3}
                    className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-black bg-white resize-none"
                    disabled={isCreating}
                  />
                </div>
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={() => {
                    setShowCreateModal(false);
                    setNewProfessionalName("");
                    setNewProfessionalDescription("");
                    setError(null);
                  }}
                  disabled={isCreating}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-black hover:bg-gray-50 disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateProfessional}
                  disabled={isCreating || !newProfessionalName.trim()}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isCreating ? "Creating..." : "Create"}
                </button>
              </div>
            </div>
          </div>
        )}

        <div
          className={`border-2 border-dashed rounded-xl p-10 text-center transition-colors ${
            isDragActive
              ? "border-blue-400 bg-blue-50"
              : isUploading
                ? "border-gray-200 bg-gray-50 opacity-50 cursor-not-allowed"
                : "border-gray-300 bg-white"
          }`}
          {...getRootProps()}
        >
          <input {...getInputProps()} />
          <div className="text-black">
            {isDragActive
              ? "Drop the files here..."
              : isUploading
                ? "Upload in progress..."
                : "Click to select files or drag and drop here"}
          </div>
          <div className="text-xs text-black mt-2">Supported: PDF, TXT, MD</div>
        </div>

        {error && (
          <div className="mt-6 text-red-500 bg-red-100 border border-red-700/50 p-4 rounded-lg text-black">
            {error}
          </div>
        )}

        {successMessage && (
          <div className="mt-6 text-green-700 bg-green-100 border border-green-700/50 p-4 rounded-lg text-black">
            {successMessage}
          </div>
        )}

        {/* Upload Button */}
        {parsedFiles.length > 0 &&
          (() => {
            const filesToUpload = parsedFiles.filter(
              (file) => !uploadedFiles.has(file.name)
            );
            const allUploaded = filesToUpload.length === 0;

            return (
              <div className="mt-6">
                <button
                  onClick={handleUpload}
                  disabled={
                    isUploading ||
                    !collectionName.trim() ||
                    allUploaded ||
                    filesToUpload.length === 0
                  }
                  className={`px-6 py-3 rounded-lg font-medium transition-colors ${
                    isUploading ||
                    !collectionName.trim() ||
                    allUploaded ||
                    filesToUpload.length === 0
                      ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                      : "bg-blue-600 text-white hover:bg-blue-700"
                  }`}
                >
                  {isUploading
                    ? "Uploading..."
                    : allUploaded
                      ? "All files already uploaded"
                      : `Upload ${filesToUpload.length} file(s) to ChromaDB`}
                </button>
                {!collectionName.trim() && (
                  <p className="text-xs text-red-500 mt-2">
                    Please enter a collection name to upload
                  </p>
                )}
                {allUploaded && collectionName.trim() && (
                  <p className="text-xs text-green-600 mt-2">
                    All files have been successfully uploaded. Upload new files
                    to add more.
                  </p>
                )}
              </div>
            );
          })()}

        {parsedFiles.length > 0 && (
          <section className="mt-10 space-y-8">
            {parsedFiles.map((pf) => {
              const uploadStatus = uploadStatuses.get(pf.name) || {
                status: "idle" as const,
                progress: 0,
              };

              return (
                <div
                  key={pf.name}
                  className="bg-gray-100 border border-gray-200 rounded-xl p-6"
                >
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <h2 className="text-xl font-semibold text-black">
                        {pf.name}
                      </h2>
                      {uploadStatus.status === "success" && (
                        <span className="text-green-600 text-lg">✓</span>
                      )}
                      {uploadStatus.status === "error" && (
                        <span className="text-red-600 text-lg">✗</span>
                      )}
                      {uploadStatus.status === "uploading" && (
                        <span className="text-blue-600 text-lg animate-pulse">
                          ⏳
                        </span>
                      )}
                    </div>
                    <span className="text-xs text-black">
                      {pf.chunks.length} chunks
                    </span>
                  </div>
                  <div className="text-xs text-black mb-3">{pf.type}</div>

                  {/* Progress Bar */}
                  {uploadStatus.status !== "idle" && (
                    <div className="mb-4">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs text-black">
                          {uploadStatus.status === "uploading"
                            ? `Uploading... ${uploadStatus.chunksUploaded || 0}/${uploadStatus.totalChunks || 0} chunks`
                            : uploadStatus.status === "success"
                              ? `Uploaded ${uploadStatus.chunksUploaded || 0} chunks successfully`
                              : uploadStatus.status === "error"
                                ? `Error: ${uploadStatus.error || "Unknown error"}`
                                : ""}
                        </span>
                        <span className="text-xs text-black">
                          {uploadStatus.progress}%
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2.5">
                        <div
                          className={`h-2.5 rounded-full transition-all duration-300 ${
                            uploadStatus.status === "success"
                              ? "bg-green-600"
                              : uploadStatus.status === "error"
                                ? "bg-red-600"
                                : "bg-blue-600"
                          }`}
                          style={{ width: `${uploadStatus.progress}%` }}
                        />
                      </div>
                    </div>
                  )}

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
              );
            })}
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
