const DB_NAME = "redline-db";
const DB_VERSION = 1;
const STORE_NAME = "pdfs";

function initDB(): Promise<IDBDatabase> {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(DB_NAME, DB_VERSION);

        request.onerror = () => {
            reject(new Error("Failed to open IndexedDB"));
        };

        request.onsuccess = (event) => {
            resolve((event.target as IDBOpenDBRequest).result);
        };

        request.onupgradeneeded = (event) => {
            const db = (event.target as IDBOpenDBRequest).result;
            if (!db.objectStoreNames.contains(STORE_NAME)) {
                db.createObjectStore(STORE_NAME);
            }
        };
    });
}

export async function storePdf(id: string, file: Blob): Promise<void> {
    const db = await initDB();
    return new Promise((resolve, reject) => {
        const transaction = db.transaction(STORE_NAME, "readwrite");
        const store = transaction.objectStore(STORE_NAME);

        const request = store.put(file, id);

        request.onsuccess = () => resolve();
        request.onerror = () => reject(new Error("Failed to store PDF in IndexedDB"));
    });
}

export async function getPdfFromStore(id: string): Promise<Blob | null> {
    const db = await initDB();
    return new Promise((resolve, reject) => {
        const transaction = db.transaction(STORE_NAME, "readonly");
        const store = transaction.objectStore(STORE_NAME);

        const request = store.get(id);

        request.onsuccess = () => {
            if (request.result) {
                resolve(request.result as Blob);
            } else {
                resolve(null);
            }
        };

        request.onerror = () => reject(new Error("Failed to retrieve PDF from IndexedDB"));
    });
}
