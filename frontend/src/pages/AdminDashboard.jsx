import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import api from '../utils/api';
import {
  LogOut, Settings, BookOpen, MapPin, Users, Ticket, BarChart3,
  Plus, Trash2, Edit3, Save, X, Upload, Loader2, Eye, EyeOff,
  ChevronDown, RefreshCw, AlertCircle, Compass, CheckCircle, GraduationCap,
  FileText, CheckCircle2
} from 'lucide-react';

// ─── KB Manager Tab ────────────────────────────────────────

function KBManager() {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState({ category: '', title: '', content: '' });
  const [saving, setSaving] = useState(false);

  // PDF Upload Modal State
  const [pdfModalOpen, setPdfModalOpen] = useState(false);
  const [selectedPdf, setSelectedPdf] = useState(null);
  const [pdfForm, setPdfForm] = useState({ title: '', category: 'academics', summary: '' });
  const [uploadingPdf, setUploadingPdf] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  const fetchEntries = useCallback(async () => {
    try {
      const res = await api.get('/knowledge');
      setEntries(res.data);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchEntries(); }, [fetchEntries]);

  const handleSave = async () => {
    if (!form.title.trim() || !form.content.trim() || !form.category.trim()) return;
    setSaving(true);
    try {
      if (editingId) {
        await api.put(`/knowledge/${editingId}`, form);
        setSuccessMsg('Knowledge entry updated and re-embedded successfully!');
      } else {
        await api.post('/knowledge', form);
        setSuccessMsg('New knowledge entry added and embedded successfully!');
      }
      setForm({ category: '', title: '', content: '' });
      setShowForm(false);
      setEditingId(null);
      fetchEntries();
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (entry) => {
    setForm({ category: entry.category, title: entry.title, content: entry.content });
    setEditingId(entry.id);
    setShowForm(true);
  };

  const handleDelete = async (id) => {
    if (!confirm('Delete this entry? This also removes it from the AI knowledge base.')) return;
    try {
      await api.delete(`/knowledge/${id}`);
      setSuccessMsg('Entry deleted and removed from AI embeddings.');
      fetchEntries();
      setTimeout(() => setSuccessMsg(''), 4000);
    } catch (err) { console.error(err); }
  };

  // Called when user selects a file from the file picker
  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      alert('Please select a valid PDF file.');
      return;
    }
    // Clean default title from filename
    const cleanTitle = file.name
      .replace(/\.pdf$/i, '')
      .replace(/[-_]/g, ' ')
      .replace(/\b\w/g, c => c.toUpperCase());

    setSelectedPdf(file);
    setPdfForm({
      title: cleanTitle,
      category: 'academics',
      summary: '',
    });
    setUploadError('');
    setPdfModalOpen(true);
    // Reset file input so same file can be picked again if desired
    e.target.value = '';
  };

  const submitPdfUpload = async (e) => {
    e.preventDefault();
    if (!selectedPdf) return;
    if (!pdfForm.title.trim()) {
      setUploadError('Please provide a document title.');
      return;
    }

    setUploadingPdf(true);
    setUploadError('');

    const formData = new FormData();
    formData.append('file', selectedPdf);
    formData.append('title', pdfForm.title.trim());
    formData.append('category', pdfForm.category.trim() || 'general');
    if (pdfForm.summary.trim()) {
      formData.append('summary', pdfForm.summary.trim());
    }

    try {
      await api.post('/knowledge/upload-pdf', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setSuccessMsg(`PDF "${pdfForm.title}" successfully parsed, summarized & embedded into AI Knowledge Base!`);
      setPdfModalOpen(false);
      setSelectedPdf(null);
      setPdfForm({ title: '', category: 'academics', summary: '' });
      fetchEntries();
      setTimeout(() => setSuccessMsg(''), 5000);
    } catch (err) {
      console.error('PDF upload failed:', err);
      const detail = err.response?.data?.detail;
      setUploadError(detail || 'Failed to upload and parse PDF. Ensure the file contains readable text.');
    } finally {
      setUploadingPdf(false);
    }
  };

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="w-8 h-8 text-campus-500 animate-spin" /></div>;

  return (
    <div className="space-y-4">
      {/* Success Notification Banner */}
      {successMsg && (
        <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 flex items-center gap-2.5 animate-slide-up shadow-sm">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
          <span className="font-medium">{successMsg}</span>
        </div>
      )}

      {/* Header & Controls */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h3 className="font-display text-lg font-bold text-campus-700">Knowledge Base</h3>
          <p className="text-xs text-gray-500">Manage documents and reference texts indexed by Chana's AI</p>
        </div>
        <div className="flex gap-2">
          <label className="btn-secondary text-sm cursor-pointer flex items-center gap-1.5 shadow-xs hover:border-campus-400">
            <Upload className="w-4 h-4 text-campus-600" />
            <span>Upload PDF</span>
            <input type="file" accept=".pdf" onChange={handleFileSelect} className="hidden" />
          </label>
          <button onClick={() => { setShowForm(true); setEditingId(null); setForm({ category: '', title: '', content: '' }); }}
            className="btn-primary text-sm flex items-center gap-1.5">
            <Plus className="w-4 h-4" /> Add Text Entry
          </button>
        </div>
      </div>

      {/* PDF Upload & Naming Modal */}
      {pdfModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs animate-fade-in">
          <div className="relative bg-white rounded-2xl shadow-2xl border border-cream-200 p-6 w-full max-w-lg animate-slide-up">
            <button
              onClick={() => !uploadingPdf && setPdfModalOpen(false)}
              disabled={uploadingPdf}
              className="absolute top-4 right-4 p-1.5 text-gray-400 hover:text-gray-600 hover:bg-cream-100 rounded-lg transition-colors cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-campus-50 rounded-xl flex items-center justify-center border border-campus-200 text-campus-600">
                <FileText className="w-5 h-5" />
              </div>
              <div>
                <h4 className="font-display font-bold text-campus-800 text-base">Upload Document to Knowledge Base</h4>
                <p className="text-xs text-gray-500">Configure title and AI context summary before indexing</p>
              </div>
            </div>

            {/* Selected File Details */}
            {selectedPdf && (
              <div className="p-3 bg-cream-50 border border-cream-200 rounded-xl flex items-center justify-between text-xs text-gray-700 mb-4">
                <div className="flex items-center gap-2 truncate">
                  <span className="font-semibold text-campus-800 truncate">{selectedPdf.name}</span>
                </div>
                <span className="badge bg-cream-200 text-gray-600 text-[11px] font-mono flex-shrink-0 ml-2">
                  {(selectedPdf.size / 1024).toFixed(1)} KB
                </span>
              </div>
            )}

            {uploadError && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700 flex items-start gap-2 mb-4 animate-shake">
                <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                <span>{uploadError}</span>
              </div>
            )}

            <form onSubmit={submitPdfUpload} className="space-y-3.5">
              <div>
                <label className="block text-xs font-semibold text-gray-700 uppercase mb-1">
                  Document Title <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={pdfForm.title}
                  onChange={(e) => setPdfForm({ ...pdfForm, title: e.target.value })}
                  placeholder="e.g. Examination Timetable & Rules 2026"
                  className="input-field text-sm"
                  disabled={uploadingPdf}
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 uppercase mb-1">
                  Category
                </label>
                <select
                  value={pdfForm.category}
                  onChange={(e) => setPdfForm({ ...pdfForm, category: e.target.value })}
                  className="input-field text-sm bg-white"
                  disabled={uploadingPdf}
                >
                  <option value="academics">Academics & Timetables</option>
                  <option value="fees">Fees & Financial Rules</option>
                  <option value="admissions">Admissions & Registration</option>
                  <option value="rules">Rules & Disciplinary Policies</option>
                  <option value="facilities">Campus Facilities & Hostels</option>
                  <option value="general">General University Information</option>
                </select>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="block text-xs font-semibold text-gray-700 uppercase">
                    What is this PDF about? (AI Scope & Summary)
                  </label>
                  <span className="text-[10px] text-campus-600 font-medium">Recommended for accuracy</span>
                </div>
                <textarea
                  rows={3}
                  value={pdfForm.summary}
                  onChange={(e) => setPdfForm({ ...pdfForm, summary: e.target.value })}
                  placeholder="e.g. Contains end-of-semester exam dates, regulations regarding permitted calculators, clearance procedures, and appeal deadlines. Students asking about exam schedules, fees clearance, or appeals should reference this."
                  className="input-field text-xs resize-y"
                  disabled={uploadingPdf}
                />
                <p className="text-[11px] text-gray-400 mt-1 leading-normal">
                  💡 <strong>Why this matters:</strong> Chana uses this summary to immediately know what questions this PDF answers without needing to parse the entire text for every query.
                </p>
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-cream-200">
                <button
                  type="button"
                  onClick={() => setPdfModalOpen(false)}
                  disabled={uploadingPdf}
                  className="btn-ghost text-xs px-3 py-2 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={uploadingPdf}
                  className="btn-primary text-xs px-4 py-2 flex items-center gap-1.5"
                >
                  {uploadingPdf ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Extracting Text & Embedding...</span>
                    </>
                  ) : (
                    <>
                      <Upload className="w-3.5 h-3.5" />
                      <span>Upload & Index Document</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add/Edit Text Form */}
      {showForm && (
        <div className="card p-5 animate-slide-up space-y-3">
          <h4 className="font-semibold text-campus-700">{editingId ? 'Edit Entry' : 'New Text Entry'}</h4>
          <div className="grid grid-cols-2 gap-3">
            <input value={form.category} onChange={e => setForm(p => ({ ...p, category: e.target.value }))}
              placeholder="Category (e.g., academic, fees)" className="input-field" />
            <input value={form.title} onChange={e => setForm(p => ({ ...p, title: e.target.value }))}
              placeholder="Title" className="input-field" />
          </div>
          <textarea value={form.content} onChange={e => setForm(p => ({ ...p, content: e.target.value }))}
            placeholder="Content — this is what the AI will use to answer questions..."
            className="input-field min-h-[120px] resize-y" />
          <div className="flex gap-2 justify-end">
            <button onClick={() => { setShowForm(false); setEditingId(null); }} className="btn-ghost text-sm">Cancel</button>
            <button onClick={handleSave} disabled={saving} className="btn-primary text-sm flex items-center gap-1.5">
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              {editingId ? 'Update' : 'Save & Embed'}
            </button>
          </div>
        </div>
      )}

      {/* Entries list */}
      <div className="space-y-2">
        {entries.length === 0 ? (
          <div className="card p-8 text-center text-gray-400">
            <BookOpen className="w-8 h-8 mx-auto mb-2 text-gray-300" />
            <p className="text-sm">No knowledge entries found. Add a text entry or upload a PDF above.</p>
          </div>
        ) : (
          entries.map(entry => (
            <div key={entry.id} className="card p-4 flex items-start justify-between group hover:border-campus-300 transition-colors">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <span className="badge bg-campus-50 text-campus-700">{entry.category}</span>
                  <h4 className="text-sm font-semibold text-gray-800">{entry.title}</h4>
                  {entry.source_doc && (
                    <span className="badge bg-cream-100 text-gray-600 text-[10px] flex items-center gap-1">
                      <FileText className="w-3 h-3 text-campus-600" /> {entry.source_doc}
                    </span>
                  )}
                </div>
                <p className="text-xs text-gray-500 line-clamp-2 leading-relaxed">{entry.content}</p>
              </div>
              <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity ml-3 flex-shrink-0">
                <button onClick={() => handleEdit(entry)} className="p-2 hover:bg-cream-200 rounded-lg transition-colors cursor-pointer" title="Edit entry">
                  <Edit3 className="w-4 h-4 text-gray-500" />
                </button>
                <button onClick={() => handleDelete(entry.id)} className="p-2 hover:bg-red-50 rounded-lg transition-colors cursor-pointer" title="Delete entry">
                  <Trash2 className="w-4 h-4 text-red-400" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// ─── Nav Node Manager Tab ──────────────────────────────────

function NavNodeManager() {
  const [nodes, setNodes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState({ name: '', synonyms: '', category: '', panoee_scene_id: '', description: '', building: '', floor: '' });
  const [saving, setSaving] = useState(false);

  // Tour configuration state (Admin Only)
  const [tourUrlInput, setTourUrlInput] = useState('');
  const [currentTourUrl, setCurrentTourUrl] = useState('');
  const [savingTour, setSavingTour] = useState(false);
  const [tourSuccessMsg, setTourSuccessMsg] = useState('');
  const [showTourPreview, setShowTourPreview] = useState(false);

  const fetchTour = useCallback(async () => {
    try {
      const res = await api.get('/navigation/tour');
      if (res.data?.tour_url) {
        setCurrentTourUrl(res.data.tour_url);
        setTourUrlInput(res.data.tour_url);
      }
    } catch (err) {
      console.error('Failed to fetch tour:', err);
    }
  }, []);

  useEffect(() => {
    fetchTour();
  }, [fetchTour]);

  /**
   * Normalize a user-pasted URL — adds https:// if no protocol given,
   * and extracts the src URL from an <iframe ...> embed code snippet.
   */
  const normalizeTourUrl = (raw) => {
    const trimmed = raw.trim();
    if (!trimmed) return '';

    // If user pasted an <iframe> embed snippet, extract the src value
    const iframeSrcMatch = trimmed.match(/src=["']([^"']+)["']/i);
    if (iframeSrcMatch) {
      const extracted = iframeSrcMatch[1].trim();
      return extracted.startsWith('http') ? extracted : `https://${extracted}`;
    }

    // Plain URL — add https:// if missing
    if (!/^https?:\/\//i.test(trimmed)) {
      return `https://${trimmed}`;
    }
    return trimmed;
  };

  const handleSaveTour = async (e) => {
    e?.preventDefault();
    setSavingTour(true);
    setTourSuccessMsg('');
    try {
      const cleanUrl = normalizeTourUrl(tourUrlInput);
      const res = await api.put('/navigation/tour', { tour_url: cleanUrl });
      setCurrentTourUrl(res.data.tour_url);
      setTourUrlInput(res.data.tour_url);
      setTourSuccessMsg('Campus 360° virtual tour updated successfully!');
      setTimeout(() => setTourSuccessMsg(''), 4000);
    } catch (err) {
      console.error('Failed to update tour:', err);
    } finally {
      setSavingTour(false);
    }
  };

  const handleClearTour = async () => {
    if (!confirm('Are you sure you want to remove the virtual tour? Students will see the preparation notice.')) return;
    setSavingTour(true);
    try {
      await api.put('/navigation/tour', { tour_url: '' });
      setCurrentTourUrl('');
      setTourUrlInput('');
      setShowTourPreview(false);
      setTourSuccessMsg('Virtual tour removed.');
      setTimeout(() => setTourSuccessMsg(''), 4000);
    } catch (err) {
      console.error('Failed to clear tour:', err);
    } finally {
      setSavingTour(false);
    }
  };

  const fetchNodes = useCallback(async () => {
    try {
      const res = await api.get('/navigation/nodes');
      setNodes(res.data);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchNodes(); }, [fetchNodes]);

  const handleSave = async () => {
    if (!form.name.trim()) return;
    setSaving(true);
    const payload = {
      ...form,
      synonyms: form.synonyms.split(',').map(s => s.trim()).filter(Boolean),
    };
    try {
      if (editingId) {
        await api.put(`/navigation/nodes/${editingId}`, payload);
      } else {
        await api.post('/navigation/nodes', payload);
      }
      setForm({ name: '', synonyms: '', category: '', panoee_scene_id: '', description: '', building: '', floor: '' });
      setShowForm(false);
      setEditingId(null);
      fetchNodes();
    } catch (err) { console.error(err); }
    finally { setSaving(false); }
  };

  const handleEdit = (node) => {
    setForm({
      name: node.name,
      synonyms: (node.synonyms || []).join(', '),
      category: node.category || '',
      panoee_scene_id: node.panoee_scene_id || '',
      description: node.description || '',
      building: node.building || '',
      floor: node.floor || '',
    });
    setEditingId(node.id);
    setShowForm(true);
  };

  const handleDelete = async (id) => {
    if (!confirm('Delete this navigation node?')) return;
    try {
      await api.delete(`/navigation/nodes/${id}`);
      fetchNodes();
    } catch (err) { console.error(err); }
  };

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="w-8 h-8 text-campus-500 animate-spin" /></div>;

  return (
    <div className="space-y-6">
      {/* 360° Virtual Tour Configuration Card (Admin Only) */}
      <div className="card p-5 space-y-4 border-l-4 border-l-campus-500">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-campus-50 rounded-xl flex items-center justify-center border border-campus-200">
              <Compass className="w-5 h-5 text-campus-600" />
            </div>
            <div>
              <h4 className="font-display font-bold text-campus-800">Campus 360° Virtual Tour (Panoee)</h4>
              <p className="text-xs text-gray-500">Configure the interactive virtual tour displayed in students' Campus Map tab</p>
            </div>
          </div>
          {currentTourUrl && (
            <span className="badge bg-emerald-50 text-emerald-700 text-xs px-2.5 py-1 border border-emerald-200 flex items-center gap-1">
              <CheckCircle className="w-3.5 h-3.5" /> Active
            </span>
          )}
        </div>

        {tourSuccessMsg && (
          <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            <span>{tourSuccessMsg}</span>
          </div>
        )}

        <form onSubmit={handleSaveTour} className="space-y-3">
          <div>
            <label className="block text-xs font-semibold text-gray-600 uppercase mb-1">
              Panoee Virtual Tour Share URL or &lt;iframe&gt; Embed
            </label>
            <input
              type="text"
              value={tourUrlInput}
              onChange={(e) => setTourUrlInput(e.target.value)}
              placeholder="e.g. https://tour.panoee.net/... or <iframe src='...'></iframe>"
              className="input-field text-sm"
            />
          </div>

          <div className="flex items-center justify-between flex-wrap gap-2 pt-1">
            <div className="flex items-center gap-2">
              <button
                type="submit"
                disabled={savingTour}
                className="btn-primary text-xs flex items-center gap-1.5 px-4 py-2"
              >
                {savingTour ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
                Save Tour URL
              </button>
              {currentTourUrl && (
                <button
                  type="button"
                  onClick={handleClearTour}
                  disabled={savingTour}
                  className="btn-ghost text-xs text-red-500 hover:bg-red-50 px-3 py-2"
                >
                  Clear Tour
                </button>
              )}
            </div>

            {currentTourUrl && (
              <button
                type="button"
                onClick={() => setShowTourPreview(!showTourPreview)}
                className="btn-secondary text-xs flex items-center gap-1.5 px-3 py-2"
              >
                {showTourPreview ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                {showTourPreview ? 'Hide Preview' : 'Live Preview'}
              </button>
            )}
          </div>
        </form>

        {showTourPreview && currentTourUrl && (
          <div className="mt-4 border border-cream-300 rounded-2xl overflow-hidden h-96 bg-gray-900 relative shadow-inner">
            <iframe
              src={normalizeTourUrl(currentTourUrl)}
              width="100%"
              height="100%"
              frameBorder="0"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; xr-spatial-tracking"
              allowFullScreen
              title="Admin Tour Preview"
              className="w-full h-full border-0"
            />
          </div>
        )}
      </div>

      <div className="flex items-center justify-between">
        <h3 className="font-display text-lg font-bold text-campus-700">Navigation Nodes ({nodes.length})</h3>
        <button onClick={() => { setShowForm(true); setEditingId(null); setForm({ name: '', synonyms: '', category: '', panoee_scene_id: '', description: '', building: '', floor: '' }); }}
          className="btn-primary text-sm flex items-center gap-1.5">
          <Plus className="w-4 h-4" /> Add Node
        </button>
      </div>

      {showForm && (
        <div className="card p-5 animate-slide-up space-y-3">
          <h4 className="font-semibold text-campus-700">{editingId ? 'Edit Node' : 'New Node'}</h4>
          <div className="grid grid-cols-2 gap-3">
            <input value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))}
              placeholder="Location Name" className="input-field" />
            <input value={form.category} onChange={e => setForm(p => ({ ...p, category: e.target.value }))}
              placeholder="Category (admin, academic, facility)" className="input-field" />
            <input value={form.building} onChange={e => setForm(p => ({ ...p, building: e.target.value }))}
              placeholder="Building" className="input-field" />
            <input value={form.floor} onChange={e => setForm(p => ({ ...p, floor: e.target.value }))}
              placeholder="Floor" className="input-field" />
            <input value={form.panoee_scene_id} onChange={e => setForm(p => ({ ...p, panoee_scene_id: e.target.value }))}
              placeholder="Panoee Scene ID" className="input-field" />
            <input value={form.synonyms} onChange={e => setForm(p => ({ ...p, synonyms: e.target.value }))}
              placeholder="Synonyms (comma-separated)" className="input-field" />
          </div>
          <textarea value={form.description} onChange={e => setForm(p => ({ ...p, description: e.target.value }))}
            placeholder="Description" className="input-field min-h-[60px] resize-y" />
          <div className="flex gap-2 justify-end">
            <button onClick={() => { setShowForm(false); setEditingId(null); }} className="btn-ghost text-sm">Cancel</button>
            <button onClick={handleSave} disabled={saving} className="btn-primary text-sm flex items-center gap-1.5">
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} Save
            </button>
          </div>
        </div>
      )}

      <div className="grid gap-2">
        {nodes.map(node => (
          <div key={node.id} className="card p-4 flex items-center justify-between group">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-campus-50 rounded-xl flex items-center justify-center">
                <MapPin className="w-5 h-5 text-campus-600" />
              </div>
              <div>
                <p className="text-sm font-semibold text-gray-800">{node.name}</p>
                <p className="text-xs text-gray-400">{node.building}{node.floor ? ` • ${node.floor}` : ''}</p>
                {node.synonyms?.length > 0 && (
                  <p className="text-[11px] text-campus-500 mt-0.5">aka: {node.synonyms.join(', ')}</p>
                )}
              </div>
            </div>
            <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button onClick={() => handleEdit(node)} className="p-2 hover:bg-cream-200 rounded-lg transition-colors">
                <Edit3 className="w-4 h-4 text-gray-500" />
              </button>
              <button onClick={() => handleDelete(node.id)} className="p-2 hover:bg-red-50 rounded-lg transition-colors">
                <Trash2 className="w-4 h-4 text-red-400" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Agent Manager Tab ─────────────────────────────────────

function AgentManager() {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: '', email: '', password: '' });
  const [saving, setSaving] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const fetchAgents = useCallback(async () => {
    try {
      const res = await api.get('/admin/agents');
      setAgents(res.data);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchAgents(); }, [fetchAgents]);

  const handleCreate = async () => {
    if (!form.name.trim() || !form.email.trim() || !form.password.trim()) return;
    setSaving(true);
    try {
      await api.post('/admin/agents', form);
      setForm({ name: '', email: '', password: '' });
      setShowForm(false);
      fetchAgents();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to create agent');
    } finally { setSaving(false); }
  };

  const toggleActive = async (agent) => {
    try {
      const endpoint = agent.is_active
        ? `/admin/agents/${agent.id}/deactivate`
        : `/admin/agents/${agent.id}/activate`;
      await api.patch(endpoint);
      fetchAgents();
    } catch (err) { console.error(err); }
  };

  const handleDelete = async (agent) => {
    if (!confirm(`Permanently delete agent "${agent.name}"? This cannot be undone. Their open tickets will be returned to the queue.`)) return;
    try {
      await api.delete(`/admin/agents/${agent.id}`);
      fetchAgents();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to delete agent');
    }
  };

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="w-8 h-8 text-campus-500 animate-spin" /></div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-display text-lg font-bold text-campus-700">Support Agents ({agents.length})</h3>
        <button onClick={() => setShowForm(true)} className="btn-primary text-sm flex items-center gap-1.5">
          <Plus className="w-4 h-4" /> Create Agent
        </button>
      </div>

      {showForm && (
        <div className="card p-5 animate-slide-up space-y-3">
          <h4 className="font-semibold text-campus-700">Create Agent Account</h4>
          <p className="text-xs text-gray-500">Agent will sign in using these credentials. They cannot self-register.</p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <input value={form.name} onChange={e => setForm(p => ({ ...p, name: e.target.value }))}
              placeholder="Full Name" className="input-field" />
            <input value={form.email} onChange={e => setForm(p => ({ ...p, email: e.target.value }))}
              placeholder="Email" type="email" className="input-field" />
            <div className="relative">
              <input value={form.password} onChange={e => setForm(p => ({ ...p, password: e.target.value }))}
                placeholder="Password" type={showPassword ? 'text' : 'password'} className="input-field pr-10" />
              <button type="button" onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>
          <div className="flex gap-2 justify-end">
            <button onClick={() => setShowForm(false)} className="btn-ghost text-sm">Cancel</button>
            <button onClick={handleCreate} disabled={saving} className="btn-primary text-sm flex items-center gap-1.5">
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />} Create
            </button>
          </div>
        </div>
      )}

      <div className="space-y-2">
        {agents.map(agent => (
          <div key={agent.id} className="card p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                agent.is_active ? 'bg-campus-100' : 'bg-gray-100'}`}>
                <Users className={`w-5 h-5 ${agent.is_active ? 'text-campus-600' : 'text-gray-400'}`} />
              </div>
              <div>
                <p className="text-sm font-semibold text-gray-800">{agent.name}</p>
                <p className="text-xs text-gray-400">{agent.email}</p>
              </div>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="badge bg-amber-50 text-amber-800 border border-amber-200 text-xs">
                ⭐ {agent.average_rating ? `${agent.average_rating} ★ (${agent.ratings_count} ratings)` : 'No ratings yet'}
              </span>
              <span className="badge bg-indigo-50 text-indigo-700 border border-indigo-200 text-xs">
                👤 {agent.active_tickets_count || 0} active tickets
              </span>
              <span className={`badge ${agent.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                {agent.is_active ? 'Active' : 'Inactive'}
              </span>
              <button onClick={() => toggleActive(agent)}
                className={`text-xs font-medium px-3 py-1.5 rounded-lg transition-colors ${
                  agent.is_active
                    ? 'text-red-600 hover:bg-red-50'
                    : 'text-green-600 hover:bg-green-50'
                }`}>
                {agent.is_active ? 'Deactivate' : 'Activate'}
              </button>
              <button onClick={() => handleDelete(agent)}
                className="text-xs font-medium px-3 py-1.5 rounded-lg text-red-700 hover:bg-red-50 transition-colors flex items-center gap-1">
                <Trash2 className="w-3.5 h-3.5" /> Delete
              </button>
            </div>
          </div>
        ))}
        {agents.length === 0 && (
          <div className="text-center py-8 text-gray-400">
            <Users className="w-10 h-10 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No agents created yet</p>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Ticket Oversight Tab ──────────────────────────────────

function TicketOversight() {
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [studentModal, setStudentModal] = useState(null);

  useEffect(() => {
    api.get('/tickets').then(r => setTickets(r.data)).catch(console.error).finally(() => setLoading(false));
  }, []);

  const getStatusBadge = (status) => {
    const cls = { open: 'badge-open', in_progress: 'badge-in-progress', resolved: 'badge-resolved' }[status] || 'badge-open';
    return <span className={cls}>{status.replace('_', ' ').toUpperCase()}</span>;
  };
  const getPriorityBadge = (priority) => {
    const cls = { critical: 'badge-critical', high: 'badge-high', medium: 'badge-medium', low: 'badge-low' }[priority] || 'badge-medium';
    return <span className={cls}>{priority.toUpperCase()}</span>;
  };

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="w-8 h-8 text-campus-500 animate-spin" /></div>;

  return (
    <div className="space-y-4">
      {studentModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setStudentModal(null)} />
          <div className="relative bg-white rounded-2xl shadow-2xl p-6 w-full max-w-sm animate-slide-up">
            <button onClick={() => setStudentModal(null)} className="absolute top-3 right-3 p-1.5 hover:bg-gray-100 rounded-lg transition-colors">
              <X className="w-4 h-4 text-gray-500" />
            </button>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 bg-campus-100 rounded-full flex items-center justify-center">
                <GraduationCap className="w-6 h-6 text-campus-600" />
              </div>
              <div>
                <p className="text-xs text-gray-400 font-medium">Student Information</p>
                <p className="font-display font-bold text-campus-700 text-base">{studentModal.name}</p>
              </div>
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between py-2 border-b border-cream-200">
                <span className="text-xs text-gray-500 font-medium">Full Name</span>
                <span className="text-sm font-semibold text-gray-800">{studentModal.name}</span>
              </div>
              <div className="flex items-center justify-between py-2">
                <span className="text-xs text-gray-500 font-medium">Reg Number</span>
                <span className="text-sm font-mono font-bold text-campus-600">{studentModal.reg_no || '—'}</span>
              </div>
            </div>
          </div>
        </div>
      )}
      <h3 className="font-display text-lg font-bold text-campus-700">All Tickets ({tickets.length})</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-gray-500 border-b border-cream-200">
              <th className="py-3 px-3 font-medium">ID</th>
              <th className="py-3 px-3 font-medium">Subject</th>
              <th className="py-3 px-3 font-medium">Student</th>
              <th className="py-3 px-3 font-medium">Category</th>
              <th className="py-3 px-3 font-medium">Status</th>
              <th className="py-3 px-3 font-medium">Priority</th>
              <th className="py-3 px-3 font-medium">Agent</th>
              <th className="py-3 px-3 font-medium">Queue</th>
              <th className="py-3 px-3 font-medium">Rating</th>
              <th className="py-3 px-3 font-medium">Created</th>
            </tr>
          </thead>
          <tbody>
            {tickets.map(t => (
              <tr key={t.id} className="border-b border-cream-100 hover:bg-cream-100/50 transition-colors">
                <td className="py-3 px-3 font-mono text-xs text-campus-600 font-bold">{t.tracking_id}</td>
                <td className="py-3 px-3 text-gray-800 max-w-[200px] truncate">{t.subject}</td>
                <td className="py-3 px-3">
                  <button
                    onClick={() => setStudentModal({ name: t.student_name, reg_no: t.student_reg_no })}
                    className="text-campus-600 hover:underline font-medium text-sm"
                  >
                    {t.student_name || '—'}
                  </button>
                </td>
                <td className="py-3 px-3 text-gray-500 text-xs">{t.category.replace('_', ' ')}</td>
                <td className="py-3 px-3">{getStatusBadge(t.status)}</td>
                <td className="py-3 px-3">{getPriorityBadge(t.priority)}</td>
                <td className="py-3 px-3 text-gray-600">{t.assigned_agent_name || <span className="text-gray-300">—</span>}</td>
                <td className="py-3 px-3 font-mono text-xs font-semibold text-amber-700">{t.queue_position ? `#${t.queue_position}` : <span className="text-gray-300">—</span>}</td>
                <td className="py-3 px-3 text-xs font-semibold text-amber-600">{t.rating ? `⭐ ${t.rating}/5` : <span className="text-gray-300">—</span>}</td>
                <td className="py-3 px-3 text-gray-400 text-xs">{new Date(t.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {tickets.length === 0 && <p className="text-center py-8 text-gray-400">No tickets yet</p>}
      </div>
    </div>
  );
}

// ─── Student Manager Tab ────────────────────────────────────

function StudentManager() {
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchStudents = useCallback(async () => {
    try {
      const res = await api.get('/admin/students');
      setStudents(res.data);
    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchStudents(); }, [fetchStudents]);

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="w-8 h-8 text-campus-500 animate-spin" /></div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-display text-lg font-bold text-campus-700">Students ({students.length})</h3>
        <button onClick={fetchStudents} className="btn-secondary text-sm flex items-center gap-1.5">
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-gray-500 border-b border-cream-200">
              <th className="py-3 px-3 font-medium">#</th>
              <th className="py-3 px-3 font-medium">Full Name</th>
              <th className="py-3 px-3 font-medium">Email</th>
              <th className="py-3 px-3 font-medium">Reg Number</th>
              <th className="py-3 px-3 font-medium">Status</th>
              <th className="py-3 px-3 font-medium">Tickets</th>
              <th className="py-3 px-3 font-medium">Joined</th>
            </tr>
          </thead>
          <tbody>
            {students.map((s, i) => (
              <tr key={s.id} className="border-b border-cream-100 hover:bg-cream-100/50 transition-colors">
                <td className="py-3 px-3 text-gray-400 text-xs">{i + 1}</td>
                <td className="py-3 px-3">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 bg-campus-100 rounded-full flex items-center justify-center flex-shrink-0">
                      <GraduationCap className="w-4 h-4 text-campus-600" />
                    </div>
                    <span className="font-semibold text-gray-800">{s.name}</span>
                  </div>
                </td>
                <td className="py-3 px-3 text-gray-500">{s.email}</td>
                <td className="py-3 px-3 font-mono text-xs font-bold text-campus-600">{s.student_reg_no || '—'}</td>
                <td className="py-3 px-3">
                  <span className={`badge ${s.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                    {s.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td className="py-3 px-3">
                  <span className="badge bg-amber-50 text-amber-700 border border-amber-200">
                    {s.ticket_count} ticket{s.ticket_count !== 1 ? 's' : ''}
                  </span>
                </td>
                <td className="py-3 px-3 text-gray-400 text-xs">{new Date(s.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {students.length === 0 && (
          <div className="text-center py-12 text-gray-400">
            <GraduationCap className="w-10 h-10 mx-auto mb-2 opacity-40" />
            <p className="text-sm">No students registered yet</p>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Analytics Tab ─────────────────────────────────────────

function AnalyticsDashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchStats = useCallback(async () => {
    try {
      const r = await api.get('/analytics/dashboard');
      setStats(r.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchStats();
  };

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="w-8 h-8 text-campus-500 animate-spin" /></div>;
  if (!stats) return <p className="text-center py-8 text-gray-400">Failed to load analytics</p>;

  const { overview, tickets_by_status, tickets_by_category, top_intents } = stats;

  const statCards = [
    { label: 'Students', value: overview.total_students, color: 'from-campus-600 to-campus-500' },
    { label: 'Agents', value: overview.total_agents, color: 'from-blue-600 to-blue-500' },
    { label: 'Tickets', value: overview.total_tickets, color: 'from-amber-600 to-amber-500' },
    { label: 'KB Entries', value: overview.total_kb_entries, color: 'from-purple-600 to-purple-500' },
    { label: 'Chat Sessions', value: overview.total_chat_sessions, color: 'from-pink-600 to-pink-500' },
    { label: 'Vector Chunks', value: overview.vector_chunks, color: 'from-teal-600 to-teal-500' },
  ];

  const maxCategoryCount = Math.max(...(tickets_by_category.map(c => c.count) || [1]));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="font-display text-lg font-bold text-campus-700">Analytics Dashboard</h3>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="btn-secondary text-sm flex items-center gap-1.5"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh Metrics
        </button>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {statCards.map((s, i) => (
          <div key={i} className={`bg-gradient-to-br ${s.color} rounded-2xl p-4 text-white animate-fade-in`} style={{ animationDelay: `${i * 50}ms` }}>
            <p className="text-xs font-medium opacity-80">{s.label}</p>
            <p className="text-2xl font-display font-bold mt-1">{s.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Tickets by Status */}
        <div className="card p-5">
          <h4 className="font-semibold text-campus-700 mb-4">Tickets by Status</h4>
          <div className="space-y-3">
            {tickets_by_status.map((item) => (
              <div key={item.status} className="flex items-center gap-3">
                <span className="text-sm text-gray-600 w-24">{item.status}</span>
                <div className="flex-1 bg-cream-200 rounded-full h-6 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      item.status === 'Open' ? 'bg-amber-400' :
                      item.status === 'In Progress' ? 'bg-blue-400' : 'bg-emerald-400'
                    }`}
                    style={{ width: `${Math.max((item.count / (overview.total_tickets || 1)) * 100, 5)}%` }}
                  />
                </div>
                <span className="text-sm font-bold text-gray-700 w-8 text-right">{item.count}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Tickets by Category */}
        <div className="card p-5">
          <h4 className="font-semibold text-campus-700 mb-4">Tickets by Category</h4>
          {tickets_by_category.length === 0 ? (
            <p className="text-sm text-gray-400">No tickets yet</p>
          ) : (
            <div className="space-y-2">
              {tickets_by_category.map((item) => (
                <div key={item.category} className="flex items-center gap-3">
                  <span className="text-xs text-gray-600 w-28 truncate">{item.category}</span>
                  <div className="flex-1 bg-cream-200 rounded-full h-5 overflow-hidden">
                    <div className="h-full bg-campus-400 rounded-full transition-all duration-500"
                      style={{ width: `${(item.count / maxCategoryCount) * 100}%` }} />
                  </div>
                  <span className="text-xs font-bold text-gray-700 w-6 text-right">{item.count}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Top Intents */}
        <div className="card p-5 lg:col-span-2">
          <h4 className="font-semibold text-campus-700 mb-4">Top Chat Intents</h4>
          {top_intents.length === 0 ? (
            <p className="text-sm text-gray-400">No chat data yet</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {top_intents.map((item) => (
                <div key={item.intent} className="badge bg-campus-50 text-campus-700 px-4 py-2">
                  {item.intent}: <span className="font-bold ml-1">{item.count}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Main Admin Dashboard ──────────────────────────────────

export default function AdminDashboard() {
  const { user, logout } = useAuth();
  const [activeTab, setActiveTab] = useState('analytics');

  const tabs = [
    { id: 'analytics', label: 'Analytics', icon: BarChart3 },
    { id: 'knowledge', label: 'Knowledge Base', icon: BookOpen },
    { id: 'navigation', label: '360° Virtual Tour', icon: Compass },
    { id: 'agents', label: 'Agents', icon: Users },
    { id: 'students', label: 'Students', icon: GraduationCap },
    { id: 'tickets', label: 'Tickets', icon: Ticket },
  ];

  return (
    <div className="flex h-screen bg-cream-100">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-cream-200 flex flex-col">
        <div className="p-5 border-b border-cream-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl overflow-hidden flex items-center justify-center bg-white shadow-sm border border-cream-200">
              <img src="/chana_logo.png" alt="Chana" className="w-8 h-8 object-contain" />
            </div>
            <div>
              <h1 className="font-display text-base font-bold text-campus-700">Chana Admin</h1>
              <p className="text-[11px] text-gray-400">{user?.name}</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 p-3 space-y-1">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={activeTab === tab.id ? 'sidebar-link-active w-full' : 'sidebar-link-inactive w-full'}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </nav>

        <div className="p-3 border-t border-cream-200">
          <button onClick={logout}
            className="sidebar-link-inactive w-full text-red-500 hover:bg-red-50 hover:text-red-600">
            <LogOut className="w-4 h-4" />
            Logout
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto">
        <div className="p-6 max-w-6xl mx-auto">
          {activeTab === 'analytics' && <AnalyticsDashboard />}
          {activeTab === 'knowledge' && <KBManager />}
          {activeTab === 'navigation' && <NavNodeManager />}
          {activeTab === 'agents' && <AgentManager />}
          {activeTab === 'students' && <StudentManager />}
          {activeTab === 'tickets' && <TicketOversight />}
        </div>
      </main>
    </div>
  );
}
