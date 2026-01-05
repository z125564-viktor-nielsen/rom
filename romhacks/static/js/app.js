/* =========================================
   1. UTILITIES & PATCHING ENGINES
   ========================================= */
// (Keep all the patching code: fill, strtest, CRC32Table, PatchStream, applyPatch... functions exactly as they were)
function fill(v, start, end) { for(var i = start; i < end; i++) this[i] = v; }
if(!Uint8Array.prototype.fill) Uint8Array.prototype.fill = fill;
function strtest(u8arr, str) { for(var i = 0; i < str.length; i++) { if(u8arr[i] != str.charCodeAt(i)) return false; } return true; }
function bytecopy(dst, dstOffs, src, srcOffs, size) { var subsrc = src.subarray(srcOffs, srcOffs + size); dst.set(subsrc, dstOffs); }
function byteswap(u8arr, offs, size) { var sub = u8arr.subarray(offs, offs + size); for(var i = 0; i < sub.byteLength; i += 2) { var t = sub[i]; sub[i] = sub[i+1]; sub[i+1] = t; } }
const CRC32Table = (function() { var table = []; for(var i = 0; i < 256; i++) { var crc = i; for(var j = 0; j < 8; j++) crc = (crc & 1) ? (crc >>> 1) ^ 0xEDB88320 : (crc >>> 1); table.push(crc >>> 0); } return table; })();
function crc32(arr, offs, size) { var crc = 0xFFFFFFFF; for(var i = 0; i < size; i++) crc = (CRC32Table[(crc & 0xFF) ^ arr[offs + i]] ^ (crc >>> 8)) >>> 0; return (~crc) >>> 0; }
function PatchStream(ab, littleEndian) { this.ab = ab; this.u8 = new Uint8Array(ab); this.dv = new DataView(ab); this.offset = 0; this.littleEndian = littleEndian || false; }
PatchStream.prototype = { seek: function(offset) { this.offset = offset; }, skip: function(numBytes) { this.offset += numBytes; }, isEOF: function() { return (this.offset >= this.ab.byteLength); }, readBytes: function(dst, dstOffs, numBytes) { bytecopy(dst, dstOffs, this.u8, this.offset, numBytes); this.skip(numBytes); }, _readInt: function(dvType, numBytes) { var val = this.dv[dvType](this.offset, this.littleEndian); this.offset += numBytes; return val; }, readU8: function() { return this._readInt('getUint8', 1); }, readU16: function() { return this._readInt('getUint16', 2); }, readU24: function() { if(!this.littleEndian) return (this.readU16() << 8) | this.readU8(); return this.readU16() | (this.readU8() << 16); }, readU32: function() { return this._readInt('getUint32', 4); }, readU64: function() { var a = this.readU32(); var b = this.readU32(); if(this.littleEndian) return ((b * 0x100000000) + a); return ((a * 0x100000000) + b); } };
const APS_MODE_SIMPLE = 0, APS_MODE_N64 = 1, APS_N64_FMT_V64 = 0;
function applyPatchAPS(sourceData, patchData, ignoreChecksums) { var patchStream = new PatchStream(patchData, true); var sourceU8 = new Uint8Array(sourceData); var sourceDV = new DataView(sourceData); patchStream.seek(0x05); var patchMode = patchStream.readU8(); patchStream.skip(0x33); var targetSize = 0; if(patchMode == APS_MODE_SIMPLE) targetSize = patchStream.readU32(); else if(patchMode == APS_MODE_N64) { var fileFormat = patchStream.readU8(); patchStream.littleEndian = false; var cartId = patchStream.readU16(); var countryCode = patchStream.readU8(); var crc1 = patchStream.readU32(); patchStream.littleEndian = true; patchStream.skip(0x09); targetSize = patchStream.readU32(); if(!ignoreChecksums) { if(fileFormat == APS_N64_FMT_V64) byteswap(sourceU8, 0, 0x40); var srcCrc1 = sourceDV.getUint32(0x10); if(crc1 != srcCrc1) throw new Error("APS Source Checksum Mismatch"); } } else throw new Error("Unknown APS mode"); var targetData = new ArrayBuffer(targetSize); var targetU8 = new Uint8Array(targetData); bytecopy(targetU8, 0, sourceU8, 0, Math.min(sourceU8.byteLength, targetSize)); while(!patchStream.isEOF()) { var targetOffs = patchStream.readU32(); var length = patchStream.readU8(); if(length != 0) patchStream.readBytes(targetU8, targetOffs, length); else { var runByte = patchStream.readU8(); var runLength = patchStream.readU8(); targetU8.fill(runByte, targetOffs, targetOffs + runLength); } } return targetData; }
function yay0decode(src) { var srcDV = new DataView(src); var srcU8 = new Uint8Array(src); var dstSize = srcDV.getUint32(0x04); var pairPos = srcDV.getUint32(0x08); var dataPos = srcDV.getUint32(0x0C); var bitsPos = 0x10; var dst = new ArrayBuffer(dstSize); var dstU8 = new Uint8Array(dst); var shift = 0, bits = 0, dstPos = 0; while(dstPos < dstSize) { if(shift == 0) { bits = srcDV.getUint32(bitsPos); bitsPos += 4; shift = 32; } if(bits & 0x80000000) dstU8[dstPos++] = srcU8[dataPos++]; else { var pair = srcDV.getUint16(pairPos); pairPos += 2; var length = pair >> 12; var offset = dstPos - (pair & 0x0FFF) - 1; if(length == 0) length = srcU8[dataPos++] + 18; else length += 2; while(length--) dstU8[dstPos++] = dstU8[offset++]; } bits <<= 1; shift--; } return dst; }
function applyPatchMOD(sourceData, patchData) { var patchStream = new PatchStream(patchData); if(strtest(patchStream.u8, 'Yay0')) { patchData = yay0decode(patchData); patchStream = new PatchStream(patchData); } patchStream.seek(4); var count = patchStream.readU32(); var targetSize = sourceData.byteLength; var tempStream = new PatchStream(patchData); tempStream.seek(4); tempStream.readU32(); for(var i=0; i<count; i++){ var tO = tempStream.readU32(); var tL = tempStream.readU32(); if(tO + tL > targetSize) targetSize = tO + tL; tempStream.skip(tL); } var targetData = new ArrayBuffer(targetSize); var targetU8 = new Uint8Array(targetData); bytecopy(targetU8, 0, new Uint8Array(sourceData), 0, sourceData.byteLength); for(var i = 0; i < count; i++) { var targetOffs = patchStream.readU32(); var length = patchStream.readU32(); patchStream.readBytes(targetU8, targetOffs, length); } return targetData; }
function applyPatchUPS(sourceData, patchData, ignoreChecksums) { function readnum(u8, offsetObj) { var num = 0, shift = 1; while(true) { var x = u8[offsetObj.o++]; num += (x & 0x7F) * shift; if(x & 0x80) break; shift <<= 7; num += shift; } return num; } var patchU8 = new Uint8Array(patchData); var sourceU8 = new Uint8Array(sourceData); if(!ignoreChecksums) { var srcCRC = new DataView(patchData).getUint32(patchData.byteLength - 12, true); if(srcCRC != crc32(sourceU8, 0, sourceU8.byteLength)) throw new Error("UPS Source Checksum Mismatch"); } var ptr = {o: 4}; var inputSize = readnum(patchU8, ptr); var outputSize = readnum(patchU8, ptr); var targetData = new ArrayBuffer(outputSize); var targetU8 = new Uint8Array(targetData); bytecopy(targetU8, 0, sourceU8, 0, Math.min(sourceU8.byteLength, outputSize)); var targetOffs = 0; while(ptr.o < patchData.byteLength - 12) { var skip = readnum(patchU8, ptr); targetOffs += skip; while(true) { var x = patchU8[ptr.o++]; if(x === 0) break; targetU8[targetOffs++] ^= x; } targetOffs++; } return targetData; }
function applyPatchBPS(sourceData, patchData, ignoreChecksums) { var sourceU8 = new Uint8Array(sourceData); var patchU8 = new Uint8Array(patchData); if(!ignoreChecksums) { var srcCRC = new DataView(patchData).getUint32(patchData.byteLength - 12, true); if(srcCRC != crc32(sourceU8, 0, sourceU8.byteLength)) throw new Error("BPS Source Checksum Mismatch"); } var ptr = {o: 4}; function readnum() { var num = 0, shift = 1; while(true) { var x = patchU8[ptr.o++]; num += (x & 0x7F) * shift; if(x & 0x80) break; shift <<= 7; num += shift; } return num; } var srcSize = readnum(); var targetSize = readnum(); var metaSize = readnum(); ptr.o += metaSize; var targetData = new ArrayBuffer(targetSize); var targetU8 = new Uint8Array(targetData); var targetOffs = 0, sourceRelativeOffs = 0, targetRelativeOffs = 0; while(ptr.o < patchData.byteLength - 12) { var data = readnum(); var command = data & 3; var length = (data >>> 2) + 1; switch(command) { case 0: bytecopy(targetU8, targetOffs, sourceU8, targetOffs, length); targetOffs += length; break; case 1: bytecopy(targetU8, targetOffs, patchU8, ptr.o, length); ptr.o += length; targetOffs += length; break; case 2: data = readnum(); sourceRelativeOffs += (data & 1 ? -1 : 1) * (data >>> 1); bytecopy(targetU8, targetOffs, sourceU8, sourceRelativeOffs, length); targetOffs += length; sourceRelativeOffs += length; break; case 3: data = readnum(); targetRelativeOffs += (data & 1 ? -1 : 1) * (data >>> 1); for(var i=0; i<length; i++) targetU8[targetOffs++] = targetU8[targetRelativeOffs++]; break; } } return targetData; }
function applyPatchIPS(sourceData, patchData) { var patchStream = new PatchStream(patchData); if(patchStream.readU8()!=80 || patchStream.readU8()!=65 || patchStream.readU8()!=84) throw new Error("Invalid IPS"); patchStream.seek(5); var targetData = new ArrayBuffer(Math.max(sourceData.byteLength, 16*1024*1024)); var targetU8 = new Uint8Array(targetData); targetU8.set(new Uint8Array(sourceData)); var maxWrite = sourceData.byteLength; while(patchStream.offset < patchData.byteLength - 3) { if(patchStream.u8[patchStream.offset] === 69 && patchStream.u8[patchStream.offset+1] === 79 && patchStream.u8[patchStream.offset+2] === 70) break; var offset = patchStream.readU24(); var length = patchStream.readU16(); if(length === 0) { var rleLen = patchStream.readU16(); var val = patchStream.readU8(); if(offset + rleLen > targetData.byteLength) throw new Error("IPS: RLE Write out of bounds"); if(offset + rleLen > maxWrite) maxWrite = offset + rleLen; targetU8.fill(val, offset, offset + rleLen); } else { if(offset + length > targetData.byteLength) throw new Error("IPS: Write out of bounds"); if(offset + length > maxWrite) maxWrite = offset + length; patchStream.readBytes(targetU8, offset, length); } } return targetData.slice(0, maxWrite); }
function applyPatchPPF(sourceData, patchData) { var patchStream = new PatchStream(patchData); patchStream.seek(56); if(new Uint8Array(patchData)[5] === 0) patchStream.skip(1024); var targetData = sourceData.slice(0); var targetU8 = new Uint8Array(targetData); while(!patchStream.isEOF()) { if(patchStream.offset + 10 > patchData.byteLength) break; var offset = Number(patchStream.readU64()); var count = patchStream.readU8(); patchStream.readBytes(targetU8, offset, count); } return targetData; }
const VCD_NOOP=0, VCD_ADD=1, VCD_RUN=2, VCD_COPY=3; const VCDDefaultCodeTable = (function(){ var t = []; var e = {inst:VCD_NOOP, size:0, mode:0}; t.push([{inst:VCD_RUN,size:0,mode:0},e]); for(var s=0;s<=17;s++) t.push([{inst:VCD_ADD,size:s,mode:0},e]); for(var m=0;m<=8;m++) { t.push([{inst:VCD_COPY,size:0,mode:m},e]); for(var s=4;s<=18;s++) t.push([{inst:VCD_COPY,size:s,mode:m},e]); } for(var m=0;m<=5;m++) for(var as=1;as<=4;as++) for(var cs=4;cs<=6;cs++) t.push([{inst:VCD_ADD,size:as,mode:0},{inst:VCD_COPY,size:cs,mode:m}]); for(var m=6;m<=8;m++) for(var as=1;as<=4;as++) t.push([{inst:VCD_ADD,size:as,mode:0},{inst:VCD_COPY,size:4,mode:m}]); for(var m=0;m<=8;m++) t.push([{inst:VCD_COPY,size:4,mode:m},{inst:VCD_ADD,size:1,mode:0}]); return t; })();
function applyPatchVCD(sourceData, patchData, ignoreChecksums) { var patchStream = new PatchStream(patchData); patchStream.skip(4); var indicator = patchStream.readU8(); if(indicator & 1) throw new Error("VCDiff: Secondary compression (LZMA) not supported in offline mode."); if(indicator & 2) throw new Error("VCDiff: Custom code table not supported."); if(indicator & 4) { var len = 0, shift = 0; while(true) { var b=patchStream.readU8(); len += (b&0x7F)<<shift; if(!(b&0x80))break; shift+=7; } patchStream.skip(len); } var targetData = new Uint8Array(sourceData.byteLength * 2); var targetPos = 0; var sourceU8 = new Uint8Array(sourceData); var cache = { near: [0,0,0,0], same: new Uint8Array(256*3).fill(0), nextSlot: 0 }; function readNum() { var num = 0, shift = 0; while(true) { var b = patchStream.readU8(); num += (b&0x7F) << shift; if(!(b&0x80)) break; shift += 7; } return num; } while(!patchStream.isEOF()) { var winIndicator = patchStream.readU8(); var srcSegLen = 0, srcSegPos = 0; if(winIndicator & 3) { srcSegLen = readNum(); srcSegPos = readNum(); } var deltaLen = readNum(); var targetWinLen = readNum(); var deltaIndicator = patchStream.readU8(); var dataLen = readNum(); var instLen = readNum(); var addrLen = readNum(); if(winIndicator & 4) patchStream.readU32(); var dataStart = patchStream.offset; var instStart = dataStart + dataLen; var addrStart = instStart + instLen; var dataStr = new PatchStream(patchData); dataStr.seek(dataStart); var instStr = new PatchStream(patchData); instStr.seek(instStart); var addrStr = new PatchStream(patchData); addrStr.seek(addrStart); var winTargetStart = targetPos; while(instStr.offset < addrStart) { var codeIdx = instStr.readU8(); var def = VCDDefaultCodeTable[codeIdx]; for(var i=0; i<2; i++) { var op = def[i]; if(op.inst === VCD_NOOP) continue; var size = op.size === 0 ? instStr.readU8() : op.size; if(op.inst === VCD_ADD) { for(var k=0; k<size; k++) targetData[targetPos++] = dataStr.readU8(); } else if(op.inst === VCD_RUN) { var b = dataStr.readU8(); for(var k=0; k<size; k++) targetData[targetPos++] = b; } else if(op.inst === VCD_COPY) { var addr = 0; var m = op.mode; if(m===0) { var n = 0, sh=0; while(true){ var x=addrStr.readU8(); n+=(x&0x7F)<<sh; if(!(x&0x80))break; sh+=7; } addr = n; } else if(m===1) { var n = 0, sh=0; while(true){ var x=addrStr.readU8(); n+=(x&0x7F)<<sh; if(!(x&0x80))break; sh+=7; } addr = targetPos - n; } else if(m >= 2 && m < 6) { var n = 0, sh=0; while(true){ var x=addrStr.readU8(); n+=(x&0x7F)<<sh; if(!(x&0x80))break; sh+=7; } addr = cache.near[m-2] + n; cache.near[m-2] = addr; } else { var b = addrStr.readU8(); addr = cache.same[(m-6)*256 + b]; } cache.near[cache.nextSlot] = addr; cache.nextSlot = (cache.nextSlot+1)%4; cache.same[addr%(256*3)] = addr; var copySrc = (winIndicator & 1) ? sourceU8 : targetData; var absAddr = (winIndicator & 1) ? (srcSegPos + addr) : addr; for(var k=0; k<size; k++) targetData[targetPos++] = copySrc[absAddr++]; } } } patchStream.seek(addrStart + addrLen); } return targetData.buffer.slice(0, targetPos); }

/* =========================================
   2. UI & FILTERING LOGIC
   ========================================= */

let activeConsole = 'all';
let currentPage = 1;
const gamesPerPage = 12;
let allCards = [];

function updatePagination() {
    const searchInput = document.getElementById('search-input');
    const query = searchInput ? searchInput.value.toLowerCase() : '';
    
    // First, get all cards that match the current filters
    const filteredCards = allCards.filter(card => {
        const cardConsole = (card.dataset.console || '').toLowerCase();
        const cardTitle = card.querySelector('h3').innerText.toLowerCase();

        const consoles = cardConsole.split(/\s+/).filter(Boolean);
        
        const matchConsole = (activeConsole === 'all' || consoles.includes(activeConsole));
        const matchSearch = (query === '' || cardTitle.includes(query));
        
        return matchConsole && matchSearch;
    });
    
    const totalPages = Math.ceil(filteredCards.length / gamesPerPage);
    
    // Hide all cards first
    allCards.forEach(card => card.style.display = 'none');
    
    // Show cards for current page
    const startIdx = (currentPage - 1) * gamesPerPage;
    const endIdx = startIdx + gamesPerPage;
    
    filteredCards.slice(startIdx, endIdx).forEach(card => {
        card.style.display = 'flex';
    });
    
    // Update pagination buttons
    document.getElementById('page-indicator').innerText = `Page ${currentPage} of ${Math.max(1, totalPages)}`;
    document.getElementById('btn-prev').disabled = currentPage === 1;
    document.getElementById('btn-next').disabled = currentPage >= totalPages || totalPages === 0;
}

function filterHacks(selectedConsole) {
    // 1. If a button was clicked, update the active console
    if (selectedConsole) {
        activeConsole = selectedConsole;
        currentPage = 1; // Reset to first page on filter change
        
        // Visual Update for Buttons
        const buttons = document.querySelectorAll('.filter-btn');
        buttons.forEach(btn => {
            btn.classList.remove('active', 'bg-green-900/50', 'text-green-300', 'border-green-500');
            btn.classList.add('bg-gray-800', 'text-gray-400', 'border-gray-700');
        });
        
        if(event && event.currentTarget && event.currentTarget.classList.contains('filter-btn')) {
            event.currentTarget.classList.remove('bg-gray-800', 'text-gray-400', 'border-gray-700');
            event.currentTarget.classList.add('active', 'bg-green-900/50', 'text-green-300', 'border-green-500');
        }
    }

    updatePagination();
}

function prevPage() {
    if (currentPage > 1) {
        currentPage--;
        updatePagination();
    }
}

function nextPage() {
    const searchInput = document.getElementById('search-input');
    const query = searchInput ? searchInput.value.toLowerCase() : '';
    
    const filteredCards = allCards.filter(card => {
        const cardConsole = (card.dataset.console || '').toLowerCase();
        const cardTitle = card.querySelector('h3').innerText.toLowerCase();

        const consoles = cardConsole.split(/\s+/).filter(Boolean);
        
        const matchConsole = (activeConsole === 'all' || consoles.includes(activeConsole));
        const matchSearch = (query === '' || cardTitle.includes(query));
        
        return matchConsole && matchSearch;
    });
    
    const totalPages = Math.ceil(filteredCards.length / gamesPerPage);
    if (currentPage < totalPages) {
        currentPage++;
        updatePagination();
    }
}

function sortHacks(criteria) {
    const grid = document.getElementById('hacks-grid');
    if(!grid) return;
    
    const cards = Array.from(grid.children);
    
    cards.sort((a, b) => {
        if(criteria === 'name') {
            const titleA = a.querySelector('h3').innerText;
            const titleB = b.querySelector('h3').innerText;
            return titleA.localeCompare(titleB);
        } else if(criteria === 'newest') {
            const dateA = a.dataset.releaseDate;
            const dateB = b.dataset.releaseDate;
            
            const dateObjA = dateA ? new Date(dateA) : new Date(0);
            const dateObjB = dateB ? new Date(dateB) : new Date(0);
            
            return dateObjB - dateObjA;
        } else if(criteria === 'oldest') {
            const dateA = a.dataset.releaseDate;
            const dateB = b.dataset.releaseDate;
            
            const dateObjA = dateA ? new Date(dateA) : new Date(0);
            const dateObjB = dateB ? new Date(dateB) : new Date(0);
            
            return dateObjA - dateObjB;
        }
        return 0;
    });
    
    cards.forEach(card => grid.appendChild(card));
    currentPage = 1; // Reset to first page after sorting
    updatePagination();
}


/* =========================================
   3. INIT & PATCHER UI LOGIC
   ========================================= */
document.addEventListener('DOMContentLoaded', () => {
    // Initialize pagination on page load
    allCards = Array.from(document.querySelectorAll('.hack-card'));
    if (allCards.length > 0) {
        updatePagination();
    }
    
    // Setup search input to reset pagination
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('keyup', () => {
            currentPage = 1;
            updatePagination();
        });
    }
    
    // --- PATCHER LOGIC ---
    const romDrop = document.getElementById('rom-drop-zone');
    if(romDrop) {
        const romInput = document.getElementById('rom-file');
        const patchDrop = document.getElementById('patch-drop-zone');
        const patchInput = document.getElementById('patch-file');
        const applyBtn = document.getElementById('apply-patch-btn');
        const consoleOutput = document.getElementById('console-output');
        const progressBar = document.getElementById('progress-bar');
        const exportRomBtn = document.getElementById('export-rom-btn');
        
        let romFile, patchFile, patchedData, patchedName;
        const log = (msg, type='info') => {
            const div = document.createElement('div');
            div.className = "console-line";
            div.innerText = `> ${msg}`;
            if(type==='error') div.classList.add('text-red-500');
            if(type==='success') div.classList.add('text-blue-500');
            consoleOutput.appendChild(div);
            consoleOutput.scrollTop = consoleOutput.scrollHeight;
        };

        const setupDragDrop = (zone, input, type) => {
            zone.onclick = () => input.click();
            zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.classList.add('dragover', 'bg-blue-900/20', 'border-blue-500'); });
            zone.addEventListener('dragleave', (e) => { e.preventDefault(); zone.classList.remove('dragover', 'bg-blue-900/20', 'border-blue-500'); });
            zone.addEventListener('drop', (e) => {
                e.preventDefault();
                zone.classList.remove('dragover', 'bg-blue-900/20', 'border-blue-500');
                if (e.dataTransfer.files.length > 0) handleFileSelection(e.dataTransfer.files[0], type, zone);
            });
            input.onchange = (e) => { if(e.target.files.length > 0) handleFileSelection(e.target.files[0], type, zone); };
        };

        const handleFileSelection = (file, type, zone) => {
            if(type === 'rom') {
                romFile = file;
                document.getElementById('rom-label').innerText = file.name;
                log(`Loaded ROM: ${file.name}`, 'success');
                zone.classList.add('active-file');
            } else if (type === 'patch') {
                patchFile = file;
                document.getElementById('patch-label').innerText = file.name;
                log(`Loaded Patch: ${file.name}`, 'success');
                zone.classList.add('active-file');
            }
            checkFiles();
        };

        setupDragDrop(romDrop, romInput, 'rom');
        setupDragDrop(patchDrop, patchInput, 'patch');

        function checkFiles() {
            if(romFile && patchFile) {
                applyBtn.innerText = "Apply Patch";
                applyBtn.removeAttribute('disabled');
                applyBtn.classList.remove('disabled', 'cursor-not-allowed', 'bg-gray-700', 'text-gray-400');
                applyBtn.classList.add('bg-blue-600', 'hover:bg-blue-500', 'text-white', 'cursor-pointer', 'shadow-[0_0_15px_rgba(59,130,246,0.4)]');
            }
        }

        applyBtn.onclick = async () => {
            if(!romFile || !patchFile) return;
            applyBtn.setAttribute('disabled', 'true');
            applyBtn.classList.add('cursor-not-allowed', 'opacity-70');
            applyBtn.innerText = "Working...";
            progressBar.style.width = '20%';
            try {
                const romBuf = await romFile.arrayBuffer();
                const patchBuf = await patchFile.arrayBuffer();
                const ext = patchFile.name.split('.').pop().toLowerCase();
                const ignoreChecksum = document.getElementById('ignore-checksum').checked;
                progressBar.style.width = '50%';
                log(`Applying .${ext.toUpperCase()} patch...`);
                await new Promise(r => setTimeout(r, 100));

                let result;
                if(ext === 'ips') result = applyPatchIPS(romBuf, patchBuf);
                else if(ext === 'bps') result = applyPatchBPS(romBuf, patchBuf, ignoreChecksum);
                else if(ext === 'ups') result = applyPatchUPS(romBuf, patchBuf, ignoreChecksum);
                else if(ext === 'aps') result = applyPatchAPS(romBuf, patchBuf, ignoreChecksum);
                else if(ext === 'mod') result = applyPatchMOD(romBuf, patchBuf);
                else if(ext === 'ppf') result = applyPatchPPF(romBuf, patchBuf);
                else if(ext === 'xdelta' || ext === 'vcdiff') result = applyPatchVCD(romBuf, patchBuf, ignoreChecksum);
                else throw new Error("Unsupported format (." + ext + ")");

                patchedData = result;
                patchedName = romFile.name.replace(/\.[^/.]+$/, "") + " (Patched)." + romFile.name.split('.').pop();
                progressBar.style.width = '100%';
                log("Success! Ready to save.", 'success');
                exportRomBtn.classList.remove('hidden');
                exportRomBtn.classList.add('flex');
                applyBtn.innerText = "Complete";
            } catch(e) {
                log(`ERROR: ${e.message}`, 'error');
                progressBar.style.width = '0%';
                applyBtn.innerText = "Failed";
                setTimeout(() => { applyBtn.removeAttribute('disabled'); applyBtn.classList.remove('cursor-not-allowed', 'opacity-70'); applyBtn.innerText = "Retry Patch"; }, 2000);
            }
        };

        exportRomBtn.onclick = () => {
            if(!patchedData) return;
            const blob = new Blob([patchedData], {type: "application/octet-stream"});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a'); a.href = url; a.download = patchedName; document.body.appendChild(a); a.click(); URL.revokeObjectURL(url);
        };
    }
});