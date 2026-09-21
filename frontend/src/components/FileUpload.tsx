import React, { useRef, useState } from "react";
import { UploadCloud, RefreshCw } from "lucide-react";

interface FileUploadProps {
  accept: string;
  acceptLabel: string;
  onFileSelect: (file: File) => void;
  isLoading: boolean;
  disabled?: boolean;
}

export function FileUpload({
  accept,
  acceptLabel,
  onFileSelect,
  isLoading,
  disabled = false,
}: FileUploadProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFileName, setSelectedFileName] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFileName(file.name);
      onFileSelect(file);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    if (disabled || isLoading) return;

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      setSelectedFileName(file.name);
      onFileSelect(file);
    }
  };

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled && !isLoading) setIsDragOver(true);
      }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={handleDrop}
      className={`relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors ${
        isDragOver
          ? "border-primary bg-primary/5"
          : "border-border bg-card hover:bg-muted/30"
      } ${disabled ? "opacity-60 cursor-not-allowed" : "cursor-pointer"}`}
      onClick={() => !disabled && !isLoading && fileInputRef.current?.click()}
    >
      <input
        type="file"
        ref={fileInputRef}
        accept={accept}
        onChange={handleFileChange}
        disabled={disabled || isLoading}
        className="hidden"
      />

      <div className="flex flex-col items-center justify-center space-y-3 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
          {isLoading ? (
            <RefreshCw className="h-6 w-6 animate-spin" />
          ) : (
            <UploadCloud className="h-6 w-6" />
          )}
        </div>

        <div className="space-y-1">
          <p className="text-sm font-semibold text-foreground">
            {isLoading
              ? "Processing File..."
              : selectedFileName
              ? `Selected: ${selectedFileName}`
              : "Click to upload or drag and drop"}
          </p>
          <p className="text-xs text-muted-foreground">{acceptLabel}</p>
        </div>
      </div>
    </div>
  );
}
