import React, { useState, useEffect } from 'react';
import { listModels, pullModel, deleteModel } from '../api';
import { Box, Download, Trash2, Loader2, HardDrive, Cloud } from 'lucide-react';

function formatSize(bytes) {
  if (!bytes) return '—';
  const gb = bytes / (1024 ** 3);
  return gb >= 1 ? `${gb.toFixed(1)} GB` : `${(bytes / (1024 ** 2)).toFixed(0)} MB`;
}

export default function ModelsPage() {
  const [models, setModels] = useState([]);
  const [pullName, setPullName] = useState('');
  const [pulling, setPulling] = useState(false);
  const [pullMsg, setPullMsg] = useState('');

  useEffect(() => { load(); }, []);
  const load = () => listModels().then(r => setModels(r.data.models || [])).catch(() => {});

  const handlePull = async () => {
    if (!pullName.trim()) return;
    setPulling(true);
    setPullMsg(`Pulling ${pullName}...`);
    try {
      await pullModel(pullName.trim());
      setPullMsg(`${pullName} pulled successfully`);
      setPullName('');
      load();
    } catch (err) {
      setPullMsg(`Pull failed: ${err?.response?.data?.detail || 'Check Ollama connection'}`);
    } finally { setPulling(false); }
  };

  const handleDelete = async (name) => {
    if (!window.confirm(`Delete model ${name}?`)) return;
    try {
      await deleteModel(name);
      load();
    } catch {}
  };

  const localModels = models.filter(m => m.source === 'ollama-local');
  const cloudModels = models.filter(m => m.source !== 'ollama-local');

  return (
    <div className="p-5 lg:p-7 max-w-5xl" data-testid="models-page">
      <div className="mb-6 animate-fade-in">
        <h1 className="text-2xl font-bold tracking-tighter" style={{ fontFamily: 'Outfit, sans-serif' }}>Models Hub</h1>
        <p className="text-xs text-[#737373] mt-0.5">Manage local Ollama models and cloud model references</p>
      </div>

      {/* Pull Model */}
      <div className="border border-white/10 bg-[#141414] p-4 mb-5 animate-fade-in" data-testid="model-pull-section">
        <div className="text-[10px] tracking-[0.15em] uppercase text-[#A0A0A0] font-mono font-bold mb-3">PULL MODEL FROM OLLAMA REGISTRY</div>
        <div className="flex gap-2">
          <input value={pullName} onChange={e => setPullName(e.target.value)} placeholder="llama3.2, qwen3-coder:30b, deepseek-r1:32b..."
            className="flex-1 bg-[#0A0A0A] border border-white/10 px-3 py-2.5 text-xs text-white font-mono outline-none focus:border-[#002FA7]"
            onKeyDown={e => e.key === 'Enter' && handlePull()} data-testid="model-pull-input" />
          <button onClick={handlePull} disabled={pulling || !pullName.trim()}
            className="flex items-center gap-1.5 bg-[#002FA7] hover:bg-[#002585] text-white px-5 py-2.5 text-[10px] tracking-wider uppercase font-mono disabled:opacity-50"
            data-testid="model-pull-button">
            {pulling ? <Loader2 size={13} className="animate-spin" /> : <Download size={13} />} PULL
          </button>
        </div>
        {pullMsg && <div className={`mt-2 text-[10px] font-mono ${pullMsg.includes('failed') ? 'text-[#FF3333]' : 'text-green-500'}`}>{pullMsg}</div>}
      </div>

      {/* Local Models */}
      <div className="mb-4">
        <div className="flex items-center gap-2 mb-3">
          <HardDrive size={14} className="text-[#002FA7]" />
          <span className="text-xs tracking-[0.15em] uppercase text-[#A0A0A0] font-mono font-bold">LOCAL MODELS ({localModels.length})</span>
        </div>
        <div className="space-y-2">
          {localModels.map(m => (
            <div key={m.name} className="border border-white/10 bg-[#141414] flex items-center gap-3 px-4 py-3" data-testid={`model-${m.name}`}>
              <Box size={14} className="text-[#002FA7] shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="text-xs text-white font-bold">{m.name}</div>
                <div className="text-[10px] text-[#737373] font-mono flex items-center gap-3 mt-0.5">
                  <span>{formatSize(m.size)}</span>
                  {m.details?.family && <span>{m.details.family}</span>}
                  {m.details?.parameter_size && <span>{m.details.parameter_size}</span>}
                  {m.details?.quantization_level && <span>{m.details.quantization_level}</span>}
                </div>
              </div>
              <button onClick={() => handleDelete(m.name)} className="p-1.5 text-[#737373] hover:text-[#FF3333] transition-colors" data-testid={`delete-model-${m.name}`}>
                <Trash2 size={13} />
              </button>
            </div>
          ))}
          {localModels.length === 0 && (
            <div className="border border-white/10 bg-[#141414] p-6 text-center text-[11px] text-[#737373]">
              No local models. Pull one from the Ollama registry above, or connect Ollama first.
            </div>
          )}
        </div>
      </div>

      {/* Cloud Models */}
      {cloudModels.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Cloud size={14} className="text-[#F59E0B]" />
            <span className="text-xs tracking-[0.15em] uppercase text-[#A0A0A0] font-mono font-bold">CLOUD MODELS ({cloudModels.length})</span>
          </div>
          <div className="space-y-2">
            {cloudModels.map(m => (
              <div key={m.name + m.source} className="border border-white/10 bg-[#141414] flex items-center gap-3 px-4 py-3">
                <Cloud size={14} className="text-[#F59E0B] shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-xs text-white">{m.name}</div>
                  <div className="text-[10px] text-[#737373] font-mono">{m.details?.provider || m.source}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
