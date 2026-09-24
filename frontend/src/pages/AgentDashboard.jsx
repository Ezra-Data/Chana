import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useSocket } from '../contexts/SocketContext';
import api from '../utils/api';
import {
  LogOut, Shield, Inbox, CheckCircle2, Clock, Send, User,
  AlertTriangle, ChevronRight, Loader2, RefreshCw, ArrowLeft, X
} from 'lucide-react';

export default function AgentDashboard() {
  const { user, logout } = useAuth();
  const { on } = useSocket();
  const [tickets, setTickets] = useState([]);
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [loading, setLoading] = useState(true);
  const [replyText, setReplyText] = useState('');
  const [sendingReply, setSendingReply] = useState(false);
  const [filter, setFilter] = useState('my_active');
  const [studentModal, setStudentModal] = useState(null); // { name, reg_no }

  const fetchTickets = useCallback(async () => {
    try {
      const response = await api.get('/tickets');
      setTickets(response.data);
    } catch (err) {
      console.error('Failed to fetch tickets:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTickets();
    const unsub1 = on('ticket:new', () => fetchTickets());
    const unsub2 = on('ticket:update', () => fetchTickets());
    const unsub3 = on('ticket:message', () => {
      fetchTickets();
      if (selectedTicket) loadTicket(selectedTicket.id);
    });
    return () => { unsub1(); unsub2(); unsub3(); };
  }, [fetchTickets, on]);

  const loadTicket = async (ticketId) => {
    try {
      const response = await api.get(`/tickets/${ticketId}`);
      setSelectedTicket(response.data);
    } catch (err) {
      console.error('Failed to load ticket:', err);
    }
  };

  const claimTicket = async (ticketId) => {
    try {
      await api.patch(`/tickets/${ticketId}/claim`);
      await loadTicket(ticketId);
      fetchTickets();
    } catch (err) {
      console.error('Failed to claim ticket:', err);
    }
  };

  const updateStatus = async (ticketId, status) => {
    try {
      await api.patch(`/tickets/${ticketId}/status`, { status });
      await loadTicket(ticketId);
      fetchTickets();
    } catch (err) {
      console.error('Failed to update status:', err);
    }
  };

  const sendReply = async () => {
    if (!replyText.trim() || !selectedTicket) return;
    setSendingReply(true);
    try {
      await api.post(`/tickets/${selectedTicket.id}/messages`, { message: replyText });
      setReplyText('');
      await loadTicket(selectedTicket.id);
    } catch (err) {
      console.error('Failed to send reply:', err);
    } finally {
      setSendingReply(false);
    }
  };

  const getStatusBadge = (status) => {
    const cls = { open: 'badge-open', in_progress: 'badge-in-progress', resolved: 'badge-resolved' }[status] || 'badge-open';
    return <span className={cls}>{status.replace('_', ' ').toUpperCase()}</span>;
  };

  const getPriorityBadge = (priority) => {
    const cls = { critical: 'badge-critical', high: 'badge-high', medium: 'badge-medium', low: 'badge-low' }[priority] || 'badge-medium';
    return <span className={cls}>{priority.toUpperCase()}</span>;
  };

  const unassignedCount = tickets.filter(t => !t.assigned_agent_name && t.status !== 'resolved').length;
  const myActiveCount = tickets.filter(t => t.assigned_agent_name === user?.name && t.status !== 'resolved').length;
  const resolvedCount = tickets.filter(t => t.status === 'resolved').length;
  const allOpenCount = tickets.filter(t => t.status !== 'resolved').length;

  const filteredTickets = tickets.filter(t => {
    if (filter === 'unassigned') return !t.assigned_agent_name && t.status !== 'resolved';
    if (filter === 'my_active') return t.assigned_agent_name === user?.name && t.status !== 'resolved';
    if (filter === 'resolved') return t.status === 'resolved';
    if (filter === 'all_open') return t.status !== 'resolved';
    return true;
  });

  // ─── Student Info Modal ───────────────────────────────────
  const StudentInfoModal = () => (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setStudentModal(null)} />
      <div className="relative bg-white rounded-2xl shadow-2xl p-6 w-full max-w-sm animate-slide-up">
        <button onClick={() => setStudentModal(null)} className="absolute top-3 right-3 p-1.5 hover:bg-gray-100 rounded-lg transition-colors">
          <X className="w-4 h-4 text-gray-500" />
        </button>
        <div className="flex items-center gap-3 mb-4">
          <div className="w-12 h-12 bg-campus-100 rounded-full flex items-center justify-center">
            <User className="w-6 h-6 text-campus-600" />
          </div>
          <div>
            <p className="text-xs text-gray-400 font-medium">Student Information</p>
            <p className="font-display font-bold text-campus-700 text-base">{studentModal?.name}</p>
          </div>
        </div>
        <div className="space-y-2">
          <div className="flex items-center justify-between py-2 border-b border-cream-200">
            <span className="text-xs text-gray-500 font-medium">Full Name</span>
            <span className="text-sm font-semibold text-gray-800">{studentModal?.name}</span>
          </div>
          <div className="flex items-center justify-between py-2">
            <span className="text-xs text-gray-500 font-medium">Reg Number</span>
            <span className="text-sm font-mono font-bold text-campus-600">{studentModal?.reg_no || '—'}</span>
          </div>
        </div>
      </div>
    </div>
  );

  // ─── Ticket Detail View ───────────────────────────────
  if (selectedTicket) {
    return (
      <div className="flex flex-col h-screen bg-cream-100">
        {studentModal && <StudentInfoModal />}
        {/* Header */}
        <header className="bg-white/80 backdrop-blur-xl border-b border-cream-200 px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl overflow-hidden flex items-center justify-center bg-white shadow-sm border border-cream-200">
              <img src="/chana_logo.png" alt="Chana" className="w-8 h-8 object-contain" />
            </div>
            <div>
              <h1 className="font-display text-lg font-bold text-campus-700 leading-tight">Chana Support Portal</h1>
              <p className="text-[11px] text-gray-400 leading-tight">Agent Workspace</p>
            </div>
          </div>
          <button onClick={logout} className="btn-ghost text-sm flex items-center gap-1.5 text-red-500 hover:bg-red-50">
            <LogOut className="w-4 h-4" /> Logout
          </button>
        </header>

        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Ticket header */}
          <div className="p-4 border-b border-cream-200 bg-white/50">
            <button onClick={() => setSelectedTicket(null)} className="btn-ghost text-sm mb-2 flex items-center gap-1">
              <ArrowLeft className="w-4 h-4" /> Back to queue
            </button>
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="font-display font-bold text-lg text-campus-700">{selectedTicket.tracking_id}</h3>
                  {getStatusBadge(selectedTicket.status)}
                  {getPriorityBadge(selectedTicket.priority)}
                  {selectedTicket.queue_position ? (
                    <span className="badge bg-amber-50 text-amber-700 border border-amber-200">
                      🔢 Queue #{selectedTicket.queue_position}
                    </span>
                  ) : null}
                  {selectedTicket.rating ? (
                    <span className="badge bg-amber-50 text-amber-800 border border-amber-200 font-semibold">
                      ⭐ Student Rating: {selectedTicket.rating}/5 Stars
                    </span>
                  ) : null}
                </div>
                <p className="text-sm text-gray-600 mt-0.5">{selectedTicket.subject}</p>
                <p className="text-xs text-gray-400 mt-0.5">
                  <button
                    onClick={() => setStudentModal({ name: selectedTicket.student_name, reg_no: selectedTicket.student_reg_no })}
                    className="text-campus-600 hover:underline font-medium cursor-pointer"
                  >
                    🎓 {selectedTicket.student_name}
                  </button>
                  {' '}• Category: {selectedTicket.category.replace('_', ' ')}
                </p>
              </div>
              <div className="flex gap-2">
                {!selectedTicket.assigned_agent_id && (
                  <button onClick={() => claimTicket(selectedTicket.id)} className="btn-primary text-sm">
                    Claim Ticket
                  </button>
                )}
                {selectedTicket.status === 'in_progress' && (
                  <button onClick={() => updateStatus(selectedTicket.id, 'resolved')} className="btn-secondary text-sm flex items-center gap-1">
                    <CheckCircle2 className="w-4 h-4" /> Resolve
                  </button>
                )}
                {selectedTicket.status === 'open' && selectedTicket.assigned_agent_id && (
                  <button onClick={() => updateStatus(selectedTicket.id, 'in_progress')} className="btn-secondary text-sm">
                    Mark In Progress
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            <div className="bg-cream-100 rounded-xl p-4 text-sm">
              <p className="text-gray-500 text-xs mb-1 font-semibold">Original Description</p>
              <p className="text-gray-700">{selectedTicket.description}</p>
              <p className="text-xs text-gray-400 mt-2">
                <Clock className="w-3 h-3 inline mr-1" />
                {new Date(selectedTicket.created_at).toLocaleString()}
              </p>
            </div>

            {(selectedTicket.messages || []).map((msg) => (
              <div key={msg.id} className={`flex ${msg.sender_type === 'agent' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%] rounded-xl p-3 text-sm ${
                  msg.sender_type === 'system'
                    ? 'bg-gray-100 text-gray-500 text-center w-full text-xs italic'
                    : msg.sender_type === 'agent'
                      ? 'bg-campus-700 text-white'
                      : 'bg-white border border-cream-300'
                }`}>
                  {msg.sender_type !== 'system' && (
                    <p className="text-xs font-semibold mb-1 opacity-70">
                      {msg.sender_type === 'agent' ? '👤 ' : '🎓 '}{msg.sender_name || msg.sender_type}
                    </p>
                  )}
                  <p>{msg.message}</p>
                  <p className="text-[10px] opacity-50 mt-1">{new Date(msg.timestamp).toLocaleString()}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Reply */}
          {selectedTicket.status !== 'resolved' && (
            <div className="border-t border-cream-200 p-4 bg-white/50">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={replyText}
                  onChange={(e) => setReplyText(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && sendReply()}
                  placeholder="Type your response..."
                  className="input-field flex-1"
                />
                <button onClick={sendReply} disabled={sendingReply || !replyText.trim()} className="btn-primary px-4">
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  // ─── Queue View ───────────────────────────────────────
  return (
    <div className="flex flex-col h-screen bg-cream-100">
      {studentModal && <StudentInfoModal />}
      <header className="bg-white/80 backdrop-blur-xl border-b border-cream-200 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl overflow-hidden flex items-center justify-center bg-white shadow-sm border border-cream-200">
            <img src="/chana_logo.png" alt="Chana" className="w-8 h-8 object-contain" />
          </div>
          <div>
            <h1 className="font-display text-lg font-bold text-campus-700">Chana Support Portal</h1>
            <p className="text-[11px] text-gray-400">Welcome, {user?.name}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {unassignedCount > 0 && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-50 text-amber-700 rounded-full text-xs font-semibold animate-pulse-soft">
              <AlertTriangle className="w-3.5 h-3.5" />
              {unassignedCount} unassigned
            </div>
          )}
          <button onClick={fetchTickets} className="btn-ghost text-sm">
            <RefreshCw className="w-4 h-4" />
          </button>
          <button onClick={logout} className="btn-ghost text-sm flex items-center gap-1.5 text-red-500 hover:bg-red-50">
            <LogOut className="w-4 h-4" /> Logout
          </button>
        </div>
      </header>

      {/* Non-redundant Agent Action Tabs */}
      <div className="px-6 py-3 bg-white/60 border-b border-cream-200 flex gap-2 overflow-x-auto">
        {[
          { id: 'my_active', label: 'My Assigned Tickets', count: myActiveCount },
          { id: 'unassigned', label: 'Tickets to Claim', count: unassignedCount },
          { id: 'resolved', label: 'Solved Tickets', count: resolvedCount },
          { id: 'all_open', label: 'All Active Queue', count: allOpenCount },
        ].map(f => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id)}
            className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all cursor-pointer ${
              filter === f.id
                ? 'bg-campus-700 text-white shadow-sm'
                : 'bg-cream-200 text-gray-700 hover:bg-cream-300'
            }`}
          >
            <span>{f.label}</span>
            <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
              filter === f.id
                ? 'bg-white/20 text-white'
                : 'bg-white text-gray-600'
            }`}>
              {f.count}
            </span>
          </button>
        ))}
      </div>

      {/* Ticket list */}
      <div className="flex-1 overflow-y-auto p-6 space-y-3">
        {loading ? (
          <div className="flex items-center justify-center h-40">
            <Loader2 className="w-8 h-8 text-campus-500 animate-spin" />
          </div>
        ) : filteredTickets.length === 0 ? (
          <div className="text-center py-16 text-gray-400">
            <Inbox className="w-12 h-12 mx-auto mb-3 opacity-40 text-campus-500" />
            <p className="font-semibold text-gray-700">No tickets in this view</p>
            <p className="text-sm mt-1 text-gray-400">When students submit issues or feedback, tickets will arrive here in real-time.</p>
          </div>
        ) : (
          filteredTickets.map((ticket) => (
            <button
              key={ticket.id}
              onClick={() => loadTicket(ticket.id)}
              className="card w-full text-left p-4 flex items-center justify-between group animate-fade-in"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <span className="font-mono text-xs text-campus-600 font-bold">{ticket.tracking_id}</span>
                  {getStatusBadge(ticket.status)}
                  {getPriorityBadge(ticket.priority)}
                  {ticket.queue_position ? (
                    <span className="badge bg-amber-50 text-amber-700 border border-amber-200 text-[10px]">
                      #{ticket.queue_position} in line
                    </span>
                  ) : null}
                  {ticket.rating ? (
                    <span className="badge bg-amber-50 text-amber-800 border border-amber-200 text-[10px] font-semibold">
                      ⭐ {ticket.rating}/5
                    </span>
                  ) : null}
                  {!ticket.assigned_agent_name && (
                    <span className="badge bg-purple-100 text-purple-700">UNASSIGNED</span>
                  )}
                </div>
                <p className="text-sm font-medium text-gray-800 truncate">{ticket.subject}</p>
                <div className="flex items-center gap-3 mt-1 text-xs text-gray-400">
                  <button
                    onClick={(e) => { e.stopPropagation(); setStudentModal({ name: ticket.student_name, reg_no: ticket.student_reg_no }); }}
                    className="text-campus-600 hover:underline font-medium"
                  >
                    🎓 {ticket.student_name}
                  </button>
                  <span>📂 {ticket.category.replace('_', ' ')}</span>
                  <span>{new Date(ticket.created_at).toLocaleDateString()}</span>
                </div>
              </div>
              <ChevronRight className="w-5 h-5 text-gray-300 group-hover:text-campus-500 transition-colors flex-shrink-0" />
            </button>
          ))
        )}
      </div>
    </div>
  );
}
