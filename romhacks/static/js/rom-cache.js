/**
 * ROM Cache Manager
 * Handles IndexedDB storage of cached ROMs for quick access in the patcher
 */

class ROMCache {
    constructor() {
        this.dbName = 'ROMHacks_PatcherCache';
        this.storeName = 'cached_roms';
        this.dbVersion = 1;
        this.db = null;
        this.init();
    }

    async init() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, this.dbVersion);
            
            request.onerror = () => reject(request.error);
            request.onsuccess = () => {
                this.db = request.result;
                resolve(this.db);
            };
            
            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                if (!db.objectStoreNames.contains(this.storeName)) {
                    const store = db.createObjectStore(this.storeName, { keyPath: 'id' });
                    store.createIndex('filename', 'filename', { unique: false });
                    store.createIndex('timestamp', 'timestamp', { unique: false });
                }
            };
        });
    }

    async addROM(file, arrayBuffer) {
        const db = this.db || await this.init();
        const id = this._generateHash(arrayBuffer);
        
        const romData = {
            id: id,
            filename: file.name,
            size: arrayBuffer.byteLength,
            data: arrayBuffer,
            timestamp: Date.now(),
            crc32: this._calculateCRC32(new Uint8Array(arrayBuffer))
        };
        
        return new Promise((resolve, reject) => {
            const transaction = db.transaction([this.storeName], 'readwrite');
            const store = transaction.objectStore(this.storeName);
            const request = store.put(romData);
            
            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve(romData);
        });
    }

    async getAllROMs() {
        const db = this.db || await this.init();
        return new Promise((resolve, reject) => {
            const transaction = db.transaction([this.storeName], 'readonly');
            const store = transaction.objectStore(this.storeName);
            const request = store.getAll();
            
            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve(request.result);
        });
    }

    async getROM(id) {
        const db = this.db || await this.init();
        return new Promise((resolve, reject) => {
            const transaction = db.transaction([this.storeName], 'readonly');
            const store = transaction.objectStore(this.storeName);
            const request = store.get(id);
            
            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve(request.result);
        });
    }

    async deleteROM(id) {
        const db = this.db || await this.init();
        return new Promise((resolve, reject) => {
            const transaction = db.transaction([this.storeName], 'readwrite');
            const store = transaction.objectStore(this.storeName);
            const request = store.delete(id);
            
            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve();
        });
    }

    async clearAll() {
        const db = this.db || await this.init();
        return new Promise((resolve, reject) => {
            const transaction = db.transaction([this.storeName], 'readwrite');
            const store = transaction.objectStore(this.storeName);
            const request = store.clear();
            
            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve();
        });
    }

    async getTotalSize() {
        const roms = await this.getAllROMs();
        return roms.reduce((total, rom) => total + rom.size, 0);
    }

    _generateHash(arrayBuffer) {
        // Simple hash based on file size and first 256 bytes
        const view = new Uint8Array(arrayBuffer);
        let hash = arrayBuffer.byteLength.toString(16);
        for (let i = 0; i < Math.min(256, view.length); i++) {
            hash += view[i].toString(16).padStart(2, '0');
        }
        return hash;
    }

    _calculateCRC32(uint8Array) {
        const CRC32Table = (function() {
            let table = [];
            for (let i = 0; i < 256; i++) {
                let crc = i;
                for (let j = 0; j < 8; j++) {
                    crc = (crc & 1) ? (crc >>> 1) ^ 0xEDB88320 : (crc >>> 1);
                }
                table.push(crc >>> 0);
            }
            return table;
        })();
        
        let crc = 0xFFFFFFFF;
        for (let i = 0; i < uint8Array.length; i++) {
            crc = (CRC32Table[(crc & 0xFF) ^ uint8Array[i]] ^ (crc >>> 8)) >>> 0;
        }
        return (~crc) >>> 0;
    }
}

// Initialize cache
const romCache = new ROMCache();

// Format bytes to human-readable size
function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}
