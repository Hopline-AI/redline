import { useState, useCallback } from "react";

export function useDragAndDrop(onFileValidate: (file: File) => void) {
    const [dragOver, setDragOver] = useState(false);

    const handleFile = useCallback(
        (file: File | undefined) => {
            if (file && (file.type === "application/pdf" || file.type === "text/plain")) {
                onFileValidate(file);
            }
        },
        [onFileValidate]
    );

    const onDragOver = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        setDragOver(true);
    };

    const onDragLeave = () => setDragOver(false);

    const onDrop = (e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        setDragOver(false);
        handleFile(e.dataTransfer.files[0]);
    };

    return { dragOver, handleFile, onDragOver, onDragLeave, onDrop };
}
