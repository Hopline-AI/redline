import { useRef, useState, useCallback } from "react";
import { Upload } from "lucide-react";

interface Props {
  onFile: (file: File) => void;
  disabled?: boolean;
}

export function FileUpload({ onFile, disabled }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const handleFile = useCallback(
    (file: File | undefined) => {
      if (file && file.type === "application/pdf" || file.type === "text/plain") {
        onFile(file);
      }
    },
    [onFile]
  );

  return (
    <div
      className={`dropzone${dragOver ? " drag-over" : ""}`}
      onClick={() => !disabled && inputRef.current?.click()}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragOver(false);
        handleFile(e.dataTransfer.files[0]);
      }}
    >
      <div className="icon">
        <Upload size={40} />
      </div>
      <p>
        <strong>Drop your policy PDF here</strong>
      </p>
      <p>
        <small className="text-light">or click to browse</small>
      </p>
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.txt"
        disabled={disabled}
        onChange={(e) => handleFile(e.target.files?.[0])}
      />
    </div>
  );
}
