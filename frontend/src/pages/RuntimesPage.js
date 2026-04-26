/**
 * RuntimesPage — View and manage agent runtimes.
 *
 * Shows all registered runtimes with health status, capabilities,
 * tier classification, and allows running tasks directly on a runtime.
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  Cpu, CheckCircle, XCircle, AlertCircle, RefreshCw,
  Loader2, Zap, ChevronDown, PlayCircle, Shield, Power, PowerOff,
} from 'lucide-react';
import { listRuntimes, runTaskOnRuntime, getRoutingPolicy, startRuntime, stopRuntime, startAllRuntimes, stopAllRuntimes, fmtErr } from '../api';

function cls(...p) { return p.filter(Boolean).join(' '); }

const TIER_STYLE = {
  first_class:  'border-[#002FA7]/30 bg-[#002FA7]/8 text-[#4477FF]',
  tier_2:       'border-emerald-500/25 bg-emerald-500/8 text-emerald-400',
  tier_3:       'border-amber-500/25 bg-amber-500/8 text-amber-400',
  experimental: 'border-red-500/25 bg-red-500/8 text-red-400',
};

const INTEGRATION_ICON = {
  native:           '⚡',
  sidecar:          '🔧',
  external_process: '🖥',
  partial:          '⚠',
  experimental:     '🧪',
};

function RuntimeCard({ runtime, onRun, onRefresh }) {
  const [expanded, setExpanded] = useState(false);
  const [running, setRunning] = useState(false);
  const [runErr, setRunErr] = useState('');
  const [instruction, setInstruction] = useState('');
  const [result, setResult] = useState(null);
  const [controlLoading, setControlLoading] = useState(false);
  const [controlErr, setControlErr] = useState('');

  const h = runtime.health || {};
  const available = h.available;
  const circuitOpen = runtime.circuit_open;
  const tierStyle = TIER_STYLE[runtime.tier] || TIER_STYLE.tier_3;

  const handleRun = async () => {
    if (!instruction.trim()) return;
    setRunning(true);
    setRunErr('');
    setResult(null);
    try {
      const r = await runTaskOnRuntime(runtime.runtime_id, { instruction, task_type: 'general' });
      setResult(r.data.result);
    } catch (e) {
      setRunErr(fmtErr(e?.response?.data?.detail) || e.message);
    } finally {
      setRunning(false);
    }
  };

  const [dockerNote, setDockerNote] = useState('');

  const handleStart = async () => {
    setControlLoading(true);
    setControlErr('');
    setDockerNote('');
    try {
      const res = await startRuntime(runtime.runtime_id);
      if (res?.data?.docker_unavailable) {
        setDockerNote('Docker lifecycle control is only available when running locally. The runtime may still respond if its HTTP endpoint is reachable.');
        setExpanded(true);
      } else {
        // Provide immediate visual confirmation if not docker_unavailable
        setDockerNote('Success: Start signal sent to ' + runtime.display_name);
        setTimeout(() => onRefresh?.(), 2000);
      }
    } catch (e) {
      setControlErr(fmtErr(e?.response?.data?.detail) || e.message || 'Failed to start runtime');
      setExpanded(true);
    } finally {
      setControlLoading(false);
    }
  };

  const handleStop = async () => {
    setControlLoading(true);
    setControlErr('');
    setDockerNote('');
    try {
      const res = await stopRuntime(runtime.runtime_id);
      if (res?.data?.docker_unavailable) {
        setDockerNote('Docker lifecycle control is only available when running locally.');
        setExpanded(true);
      } else {
        setDockerNote('Success: Stop signal sent to ' + runtime.display_name);
        setTimeout(() => onRefresh?.(), 2000);
      }
    } catch (e) {
      setControlErr(fmtErr(e?.response?.data?.detail) || e.message || 'Failed to stop runtime');
      setExpanded(true);
    } finally {
      setControlLoading(false);
    }
  };

  return (
    <div className={cls(
      'bg-[#111] border rounded-xl transition-all',
      circuitOpen ? 'border-amber-500/20' :
      available ? 'border-white/8 hover:border-white/14' :
      available === false ? 'border-red-500/10 opacity-70' : 'border-white/8',
    )}>
      <div className="w-full p-4">
        <div className="flex items-start gap-3">
          <button 
            className="flex-1 text-left flex items-start gap-3 min-w-0" 
            onClick={() => setExpanded(e => !e)}
            aria-expanded={expanded}
          >
            <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-white/5 border border-white/8 text-lg flex-shrink-0">
              {INTEGRATION_ICON[runtime.integration_mode] || '🤖'}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap mb-1">
                <span className="text-[13px] font-semibold text-white">{runtime.display_name}</span>
                <span className={cls('text-[9px] px-2 py-0.5 rounded-full border font-mono', tierStyle)}>
                  {runtime.tier?.replace('_', ' ')}
                </span>
                <span className="text-[9px] font-mono text-[#444] border border-white/5 px-1.5 py-0.5 rounded">
                  {runtime.integration_mode?.replace('_', ' ')}
                </span>
              </div>
              <p className="text-[10px] text-[#555] line-clamp-1">{runtime.description}</p>
            </div>
          </button>

          <div className="flex items-center gap-2 flex-shrink-0">
            <div className="text-right mr-2">
              {circuitOpen ? (
                <div className="text-[10px] text-amber-400 flex items-center gap-1"><AlertCircle size={10} /> Circuit Open</div>
              ) : available ? (
                <div className="text-[10px] text-emerald-400 flex items-center gap-1"><CheckCircle size={10} /> Online</div>
              ) : available === false ? (
                <div className="text-[10px] text-red-400 flex items-center gap-1"><XCircle size={10} /> Offline</div>
              ) : (
                <div className="text-[10px] text-[#555]">Checking...</div>
              )}
              {h.latency_ms != null && (
                <div className="text-[9px] text-[#444]">{Math.round(h.latency_ms)}ms</div>
              )}
            </div>
            {(!available || circuitOpen) && (
              <button 
                onClick={(e) => { e.stopPropagation(); handleStart(); }} 
                disabled={controlLoading}
                className="flex items-center gap-1 px-3 py-1.5 bg-emerald-500/20 border border-emerald-500/30 text-[10px] text-emerald-400 rounded hover:bg-emerald-500/30 transition-colors disabled:opacity-40 min-w-[70px] justify-center"
              >
                {controlLoading ? <Loader2 size={12} className="animate-spin" /> : <Power size={12} />} 
                <span>Start</span>
              </button>
            )}
            {available && !circuitOpen && (
              <button 
                onClick={(e) => { e.stopPropagation(); handleStop(); }} 
                disabled={controlLoading}
                className="flex items-center gap-1 px-3 py-1.5 bg-red-500/20 border border-red-500/30 text-[10px] text-red-400 rounded hover:bg-red-500/30 transition-colors disabled:opacity-40 min-w-[70px] justify-center"
              >
                {controlLoading ? <Loader2 size={12} className="animate-spin" /> : <PowerOff size={12} />} 
                <span>Stop</span>
              </button>
            )}
            <button 
              onClick={() => setExpanded(e => !e)}
              className="p-1 hover:bg-white/5 rounded transition-colors text-[#444] hover:text-white"
            >
              <ChevronDown size={14} className={cls('transition-transform', expanded ? 'rotate-180' : '')} />
            </button>
          </div>
        </div>
      </div>

      {expanded && (
        <div className="px-4 pb-4 border-t border-white/5 pt-3 space-y-4">
          {/* Control error */}
          {controlErr && <div className="text-[10px] text-red-400">{controlErr}</div>}
          {dockerNote && (
            <div className="text-[10px] text-[#4477FF] bg-[#002FA7]/8 border border-[#002FA7]/20 rounded px-3 py-2">
              ℹ️ {dockerNote}
            </div>
          )}

          {/* Capabilities */}
          <div>
            <div className="text-[9px] uppercase tracking-widest text-[#444] mb-2">Capabilities</div>
            <div className="flex flex-wrap gap-1.5">
              {(runtime.capabilities || []).map(c => (
                <span key={c} className="text-[9px] font-mono px-2 py-0.5 rounded border border-white/8 bg-white/4 text-[#666]">
                  {c.replace(/_/g, ' ')}
                </span>
              ))}
            </div>
          </div>

          {/* Health details */}
          {h.version && (
            <div className="text-[10px] text-[#555]">Version: <span className="text-[#888] font-mono">{h.version}</span></div>
          )}
          {h.error && (
            <div className="text-[10px] text-red-400 font-mono bg-red-500/5 border border-red-500/10 rounded px-3 py-2">{h.error}</div>
          )}

          {/* Docs link */}
          {runtime.docs_url && (
            <a href={runtime.docs_url} target="_blank" rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-[10px] text-[#002FA7] hover:text-[#4477FF] transition-colors">
              View Documentation →
            </a>
          )}

          {/* Run task */}
          {available && (
            <div className="border-t border-white/5 pt-3">
              <div className="text-[9px] uppercase tracking-widest text-[#444] mb-2">Quick Run</div>
              <div className="flex gap-2">
                <input value={instruction} onChange={e => setInstruction(e.target.value)}
                  placeholder="Enter task instruction..."
                  className="flex-1 bg-black/30 border border-white/8 rounded-md px-3 py-2 text-[11px] font-mono text-white placeholder-[#444] outline-none focus:border-[#002FA7]" />
                <button onClick={handleRun} disabled={running || !instruction.trim()}
                  className="flex items-center gap-1.5 px-3 py-2 bg-[#002FA7]/20 border border-[#002FA7]/30 text-[#4477FF] text-[10px] rounded-md hover:bg-[#002FA7]/30 transition-colors disabled:opacity-40">
                  {running ? <Loader2 size={10} className="animate-spin" /> : <PlayCircle size={10} />} Run
                </button>
              </div>
              {runErr && <div className="mt-2 text-[10px] text-red-400">{runErr}</div>}
              {result && (
                <div className="mt-2">
                  <div className="text-[9px] uppercase tracking-widest text-[#444] mb-1">Output</div>
                  <pre className="text-[10px] font-mono text-[#888] bg-black/30 rounded-md p-3 whitespace-pre-wrap max-h-32 overflow-y-auto">
                    {result.output || '(no output)'}
                  </pre>
                  {result.model_used && (
                    <div className="text-[9px] text-[#444] mt-1">Model: {result.model_used}</div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function RuntimesPage() {
  const [runtimes, setRuntimes] = useState([]);
  const [policy, setPolicy] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [controlLoading, setControlLoading] = useState(false);
  const [success, setSuccess] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [rr, pr] = await Promise.allSettled([
        listRuntimes().then(r => setRuntimes(r.data.runtimes || [])),
        getRoutingPolicy().then(r => setPolicy(r.data.policy)),
      ]);
      if (rr.status === 'rejected') setError(fmtErr(rr.reason?.response?.data?.detail) || rr.reason?.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleStartAll = async (e) => {
    e?.stopPropagation();
    setControlLoading(true);
    setError('');
    setSuccess('Signal sent: Starting all runtimes...');
    try {
      const res = await startAllRuntimes();
      const rts = Object.values(res?.data?.runtimes || {});
      if (rts.some(r => r.docker_unavailable)) {
        setError('Docker lifecycle control is only available locally. Cannot auto-start runtimes here.');
        setSuccess('');
        load();
      } else if (res?.data?.partial) {
        setError('Some runtimes failed to start. Expand individual cards for details.');
        setSuccess('');
        load();
      } else {
        setSuccess('All eligible runtimes are starting.');
        setTimeout(() => { setSuccess(''); load(); }, 3000);
      }
    } catch (e) {
      setError(fmtErr(e?.response?.data?.detail) || e.message || 'Failed to start all runtimes');
      setSuccess('');
    } finally {
      setControlLoading(false);
    }
  };

  const handleStopAll = async (e) => {
    e?.stopPropagation();
    setControlLoading(true);
    setError('');
    setSuccess('Signal sent: Stopping all runtimes...');
    try {
      const res = await stopAllRuntimes();
      const rts = Object.values(res?.data?.runtimes || {});
      if (rts.some(r => r.docker_unavailable)) {
        setError('Docker lifecycle control is only available locally. Cannot auto-stop runtimes here.');
        setSuccess('');
        load();
      } else if (res?.data?.partial) {
        setError('Some runtimes failed to stop. Expand individual cards for details.');
        setSuccess('');
        load();
      } else {
        setSuccess('All eligible runtimes are stopping.');
        setTimeout(() => { setSuccess(''); load(); }, 3000);
      }
    } catch (e) {
      setError(fmtErr(e?.response?.data?.detail) || e.message || 'Failed to stop all runtimes');
      setSuccess('');
    } finally {
      setControlLoading(false);
    }
  };

  useEffect(() => { load(); }, [load]);

  const online = runtimes.filter(r => r.health?.available === true && !r.circuit_open).length;
  const offline = runtimes.length - online;

  return (
    <div className="p-5 sm:p-6 lg:p-8 max-w-5xl mx-auto">
      <div className="mb-6">
        <div className="flex items-end justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white" style={{ fontFamily: 'Outfit, sans-serif' }}>
              Runtimes
            </h1>
            <p className="text-sm text-[#555] mt-1">Pluggable agent execution environments</p>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-[11px] text-emerald-400">{online} online</span>
            {offline > 0 && <span className="text-[11px] text-red-400">{offline} offline</span>}
            {offline > 0 && (
              <button onClick={handleStartAll} disabled={controlLoading}
                className="flex items-center gap-1 px-3 py-2 bg-emerald-500/20 border border-emerald-500/30 text-[11px] text-emerald-400 rounded-md hover:bg-emerald-500/30 transition-colors disabled:opacity-40">
                {controlLoading ? <Loader2 size={11} className="animate-spin" /> : <Power size={11} />} Start All
              </button>
            )}
            {online > 0 && (
              <button onClick={handleStopAll} disabled={controlLoading}
                className="flex items-center gap-1 px-3 py-2 bg-red-500/20 border border-red-500/30 text-[11px] text-red-400 rounded-md hover:bg-red-500/30 transition-colors disabled:opacity-40">
                {controlLoading ? <Loader2 size={11} className="animate-spin" /> : <PowerOff size={11} />} Stop All
              </button>
            )}
            <button onClick={load} disabled={loading || controlLoading} className="text-[#444] hover:text-[#888] transition-colors">
              <RefreshCw size={12} className={loading || controlLoading ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="mb-6 px-4 py-3 bg-red-500/10 border border-red-500/30 rounded-xl text-[12px] text-red-400 flex items-center gap-3 animate-in fade-in slide-in-from-top-2 duration-300">
          <AlertCircle size={14} className="flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {success && (
        <div className="mb-6 px-4 py-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-[12px] text-emerald-400 flex items-center gap-3 animate-in fade-in slide-in-from-top-2 duration-300">
          <CheckCircle size={14} className="flex-shrink-0" />
          <span>{success}</span>
        </div>
      )}

      {/* Routing policy summary */}
      {policy && (
        <div className="mb-5 p-4 bg-[#0A0A0A] border border-white/8 rounded-xl">
          <div className="flex items-center gap-2 mb-2">
            <Shield size={12} className="text-[#555]" />
            <span className="text-[11px] font-semibold tracking-widest uppercase text-[#555]">Active Routing Policy</span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <div>
              <div className="text-[9px] text-[#444]">Paid Providers</div>
              <div className={cls('text-[11px] font-mono', policy.never_use_paid_providers ? 'text-red-400' : 'text-amber-400')}>
                {policy.never_use_paid_providers ? '🔒 Never' : '⚠ Allowed'}
              </div>
            </div>
            <div>
              <div className="text-[9px] text-[#444]">Default Runtime</div>
              <div className="text-[11px] font-mono text-white">{policy.preferred_runtime_id || 'auto'}</div>
            </div>
            <div>
              <div className="text-[9px] text-[#444]">Approval Required</div>
              <div className="text-[11px] font-mono text-white">
                {policy.require_approval_before_paid_escalation ? 'Yes' : 'No'}
              </div>
            </div>
          </div>
        </div>
      )}

      {loading ? (
        <div className="flex items-center gap-2 justify-center text-[#555] py-12 text-sm">
          <Loader2 size={15} className="animate-spin" /> Loading runtimes...
        </div>
      ) : runtimes.length === 0 ? (
        <div className="text-center py-12 text-[#444]">
          <Cpu size={32} className="mx-auto mb-3 opacity-30" />
          <p className="text-sm">No runtimes registered.</p>
          <p className="text-[11px] mt-1">Configure runtime adapters in server settings.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {runtimes.map(r => (
            <RuntimeCard key={r.runtime_id} runtime={r} onRefresh={load} />
          ))}
        </div>
      )}
    </div>
  );
}
