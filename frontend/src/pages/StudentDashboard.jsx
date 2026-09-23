import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useSocket } from '../contexts/SocketContext';
import api from '../utils/api';
import { PANOEE_BASE_URL, TICKET_CATEGORY_LABELS } from '../utils/constants';
import {
  MessageSquare, Ticket, Map, LogOut, Send, Bot, User,
  MapPin, ExternalLink, Clock, AlertCircle, ChevronRight,
  Search, Plus, Loader2, CheckCircle2, Circle, Timer, X,
  Compass, Settings, ArrowRight, RotateCcw, Star, History
} from 'lucide-react';

// ─── Interactive Message Content Renderer ──────────────────
// Parses message text to convert "Campus Map tab" and "My Tickets tab" / TKT IDs into clickable green links

function MessageContent({ text, onNavigate, metadata }) {
  if (!text) return null;

  // Strict regex: matches only exact tokens:
  // "Campus Map tab", "campus tab", "Campus Map", "My Tickets tab", "My Tickets", or "TKT-XXXX"
  const targetRegex = /(Campus Map tab|campus tab|Campus Map|My Tickets tab|My Tickets|TKT-\d+)/gi;
  const parts = text.split(targetRegex);

  return (
    <div className="whitespace-pre-wrap text-sm leading-relaxed">
      {parts.map((part, index) => {
        const lower = part.toLowerCase();
        const isNavMatch = lower === 'campus map tab' || lower === 'campus tab' || lower === 'campus map';
        const isTicketMatch = lower === 'my tickets tab' || lower === 'my tickets' || /^tkt-\d+$/i.test(part);

        if (isNavMatch) {
          return (
            <button
              key={index}
              type="button"
              onClick={() => onNavigate('navigation')}
              className="inline-flex items-center gap-1 font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 hover:text-emerald-900 border border-emerald-300 rounded px-1.5 py-0.5 mx-0.5 text-xs transition-colors align-baseline cursor-pointer"
              title="Click to open Campus Map"
            >
              <MapPin className="w-3 h-3 text-emerald-600 inline" />
              <span>{part}</span>
              <ExternalLink className="w-2.5 h-2.5 text-emerald-600 inline" />
            </button>
          );
        }

        if (isTicketMatch) {
          const targetTicket = /^tkt-\d+$/i.test(part) ? part.toUpperCase() : (metadata?.ticket_id || null);
          return (
            <button
              key={index}
              type="button"
              onClick={() => onNavigate('tickets', targetTicket)}
              className="inline-flex items-center gap-1 font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 hover:text-emerald-900 border border-emerald-300 rounded px-1.5 py-0.5 mx-0.5 text-xs transition-colors align-baseline cursor-pointer"
              title="Click to view in My Tickets"
            >
              <Ticket className="w-3 h-3 text-emerald-600 inline" />
              <span>{part}</span>
              <ArrowRight className="w-2.5 h-2.5 text-emerald-600 inline" />
            </button>
          );
        }

        // Render normal text with markdown bold support (**bold**)
        const boldParts = part.split(/(\*\*.*?\*\*)/g);
        return boldParts.map((subPart, subIdx) => {
          if (subPart.startsWith('**') && subPart.endsWith('**')) {
            return (
              <strong key={`${index}-${subIdx}`} className="font-semibold text-gray-900">
                {subPart.slice(2, -2)}
              </strong>
            );
          }
          return subPart;
        });
      })}
    </div>
  );
}

// ─── Chat Tab ──────────────────────────────────────────────

function ChatTab({ onNavigate, messages, setMessages, sessionId, setSessionId }) {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [showHistory, setShowHistory] = useState(false);
  const [loadingSessions, setLoadingSessions] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(scrollToBottom, [messages]);

  const fetchSessions = useCallback(async () => {
    setLoadingSessions(true);
    try {
      const res = await api.get('/chat/sessions');
      setSessions(res.data || []);
    } catch (err) {
      console.error('Failed to fetch chat sessions:', err);
    } finally {
      setLoadingSessions(false);
    }
  }, []);

  const loadSession = async (sessId) => {
    try {
      const res = await api.get(`/chat/sessions/${sessId}/messages`);
      setSessionId(sessId);
      if (res.data && res.data.length > 0) {
        setMessages(res.data);
      } else {
        setMessages([{
          id: 'welcome-' + sessId,
          role: 'assistant',
          content: "Chat session loaded. How can I help you?",
          timestamp: new Date().toISOString(),
        }]);
      }
      setShowHistory(false);
    } catch (err) {
      console.error('Failed to load session messages:', err);
    }
  };

  const handleDeleteSession = async (sessId, e) => {
    e.stopPropagation();
    if (!confirm('Delete this conversation? This cannot be undone.')) return;
    try {
      await api.delete(`/chat/sessions/${sessId}`);
      // If we deleted the current session, reset to fresh welcome
      if (sessId === sessionId) {
        setSessionId(null);
        setMessages([{
          id: 'welcome-' + Date.now(),
          role: 'assistant',
          content: "👋 Hi there! I'm Chana, your university Chatbot & Navigation assistant. I can help you with:\n\n• **Campus information** — timetables, fees, rules, procedures\n• **Finding locations** — head to the Campus Map tab to explore\n• **Reporting issues** — complaints are tracked with a ticket ID\n• **Checking ticket status** — just ask about your ticket\n\nHow can I help you today?",
          timestamp: new Date().toISOString(),
        }]);
      }
      fetchSessions();
    } catch (err) {
      console.error('Failed to delete session:', err);
    }
  };

  // Load chat history from backend on first mount if empty
  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const res = await api.get('/chat/history');
        // Only set sessionId if we got a real one (null means new user)
        if (res.data?.session_id) {
          setSessionId(res.data.session_id);
        }
        if (res.data?.messages && res.data.messages.length > 0) {
          setMessages(res.data.messages);
        } else if (!messages || messages.length === 0) {
          setMessages([{
            id: 'welcome',
            role: 'assistant',
            content: "👋 Hi there! I'm Chana, your university Chatbot & Navigation assistant. I can help you with:\n\n• **Campus information** — timetables, fees, rules, procedures\n• **Finding locations** — head to the Campus Map tab to explore\n• **Reporting issues** — complaints are tracked with a ticket ID\n• **Checking ticket status** — just ask about your ticket\n\nHow can I help you today?",
            timestamp: new Date().toISOString(),
          }]);
        }
      } catch (err) {
        console.error('Failed to load chat history:', err);
      }
    };

    if (!messages || messages.length === 0) {
      fetchHistory();
    }
    fetchSessions();
  }, []);

  const handleNewChat = async () => {
    setClearing(true);
    try {
      const res = await api.post('/chat/new-session');
      setSessionId(res.data.session_id);
      setMessages([{
        id: 'welcome-' + Date.now(),
        role: 'assistant',
        content: "👋 Hi there! Starting a fresh conversation. How can I help you today?",
        timestamp: new Date().toISOString(),
      }]);
      fetchSessions();
      setShowHistory(false);
    } catch (err) {
      console.error('Failed to start new chat:', err);
    } finally {
      setClearing(false);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await api.post('/chat/message', {
        message: userMessage.content,
        session_id: sessionId,
      });

      const botResponse = {
        id: Date.now() + 1,
        role: 'assistant',
        content: response.data.message,
        timestamp: new Date().toISOString(),
        intent: response.data.intent,
        metadata: response.data.metadata,
        is_fallback: response.data.is_fallback,
      };

      setMessages(prev => [...prev, botResponse]);
      setSessionId(response.data.session_id);
      fetchSessions();
    } catch (err) {
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'assistant',
        content: "Sorry, I'm having trouble processing your request. Please try again.",
        timestamp: new Date().toISOString(),
        is_fallback: true,
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="flex flex-col h-full relative">
      {/* Chat header toolbar */}
      <div className="px-4 py-2 bg-white/70 backdrop-blur-sm border-b border-cream-200 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          <span className="text-xs font-semibold text-campus-800">Chana Active</span>
          <span className="text-[11px] text-gray-400">• Chats saved in real-time</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => { setShowHistory(!showHistory); fetchSessions(); }}
            className={`btn-ghost text-xs px-2.5 py-1 flex items-center gap-1.5 rounded-lg border border-cream-200 cursor-pointer transition-colors ${
              showHistory ? 'bg-campus-100 text-campus-800 font-semibold' : 'text-gray-600 hover:bg-cream-100'
            }`}
            title="View previous conversations"
          >
            <Clock className="w-3.5 h-3.5 text-campus-600" />
            <span>Past Chats {sessions.length > 0 ? `(${sessions.length})` : ''}</span>
          </button>
          <button
            onClick={handleNewChat}
            disabled={clearing}
            className="btn-ghost text-xs text-campus-700 hover:bg-campus-50 px-2.5 py-1 flex items-center gap-1.5 rounded-lg border border-cream-200 cursor-pointer"
            title="Start fresh conversation"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${clearing ? 'animate-spin' : ''}`} />
            <span>New Chat</span>
          </button>
        </div>
      </div>

      {/* Past Conversations Drawer */}
      {showHistory && (
        <div className="bg-cream-50/95 border-b border-cream-200 p-3 max-h-56 overflow-y-auto animate-slide-up shadow-inner z-10">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-xs font-bold text-campus-800 uppercase tracking-wide flex items-center gap-1.5">
              <History className="w-3.5 h-3.5" /> Previous Conversations
            </h4>
            <button onClick={() => setShowHistory(false)} className="text-xs text-gray-400 hover:text-gray-600 cursor-pointer">✕ Close</button>
          </div>
          {loadingSessions ? (
            <div className="py-4 text-center"><Loader2 className="w-4 h-4 animate-spin text-campus-600 mx-auto" /></div>
          ) : sessions.length === 0 ? (
            <p className="text-xs text-gray-400 py-3 text-center">No previous conversations yet.</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
              {sessions.map((sess) => (
                <div
                  key={sess.id}
                  className={`relative group text-left p-2.5 rounded-xl border text-xs flex flex-col justify-between transition-all ${
                    sessionId === sess.id
                      ? 'bg-white border-campus-500 shadow-xs ring-1 ring-campus-400'
                      : 'bg-white/80 border-cream-200 hover:bg-white hover:border-campus-300'
                  }`}
                >
                  <button
                    onClick={() => loadSession(sess.id)}
                    className="flex-1 text-left w-full"
                  >
                    <p className={`truncate font-medium mb-1 ${
                      sessionId === sess.id ? 'text-campus-900 font-semibold' : 'text-gray-700'
                    }`}>{sess.preview || `Conversation #${sess.id}`}</p>
                    <div className="flex items-center justify-between text-[10px] text-gray-400 pt-1 border-t border-cream-100">
                      <span>{new Date(sess.updated_at || sess.created_at).toLocaleDateString()}</span>
                      <span className="badge bg-cream-100 text-gray-600 text-[10px] px-1.5 py-0.2">
                        {sess.message_count} msgs
                      </span>
                    </div>
                  </button>
                  {/* Delete button */}
                  <button
                    onClick={(e) => handleDeleteSession(sess.id, e)}
                    title="Delete this conversation"
                    className="absolute top-1.5 right-1.5 p-1 rounded-md opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-50 text-gray-400 hover:text-red-500"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} message-appear`}>
            <div className="flex gap-2 max-w-[85%]">
              {msg.role === 'assistant' && (
                <div className="flex-shrink-0 w-8 h-8 bg-campus-100 rounded-full flex items-center justify-center mt-1">
                  <Bot className="w-4 h-4 text-campus-700" />
                </div>
              )}
              <div>
                <div className={msg.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-bot'}>
                  <MessageContent
                    text={msg.content}
                    onNavigate={onNavigate}
                    metadata={msg.metadata}
                  />
                </div>

                {/* Direct Action: Open Ticket in My Tickets */}
                {msg.metadata?.ticket_id && (
                  <button
                    onClick={() => onNavigate('tickets', msg.metadata.ticket_id)}
                    className="mt-2 inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-emerald-50 text-emerald-800 
                               rounded-xl text-xs font-semibold hover:bg-emerald-100 transition-colors border border-emerald-300 shadow-2xs cursor-pointer"
                  >
                    <Ticket className="w-3.5 h-3.5 text-emerald-600" />
                    Open Ticket {msg.metadata.ticket_id} in My Tickets
                    <ArrowRight className="w-3.5 h-3.5 text-emerald-600" />
                  </button>
                )}

                {/* Direct Action: Navigation deep-link */}
                {(msg.intent === 'navigation' || msg.metadata?.type === 'nav_link') && (
                  <button
                    onClick={() => onNavigate('navigation', msg.metadata?.panoee_scene_id, msg.metadata?.node_name)}
                    className="mt-2 inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-emerald-50 text-emerald-800 
                               rounded-xl text-xs font-semibold hover:bg-emerald-100 transition-colors border border-emerald-300 shadow-2xs cursor-pointer"
                  >
                    <MapPin className="w-3.5 h-3.5 text-emerald-600" />
                    {msg.metadata?.node_name ? `View ${msg.metadata.node_name} on Campus Map` : 'Explore Campus Map'}
                    <ExternalLink className="w-3 h-3 text-emerald-600" />
                  </button>
                )}

                {/* Create ticket button on fallback */}
                {msg.metadata?.show_create_ticket && (
                  <button
                    onClick={() => onNavigate('tickets')}
                    className="mt-2 inline-flex items-center gap-2 px-4 py-2 bg-amber-50 text-amber-700 
                               rounded-xl text-sm font-medium hover:bg-amber-100 transition-colors border border-amber-200 cursor-pointer"
                  >
                    <Ticket className="w-4 h-4" />
                    Create Support Ticket
                  </button>
                )}
                <p className="text-[10px] text-gray-400 mt-1 px-1">
                  {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </p>
              </div>
              {msg.role === 'user' && (
                <div className="flex-shrink-0 w-8 h-8 bg-campus-700 rounded-full flex items-center justify-center mt-1">
                  <User className="w-4 h-4 text-white" />
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Typing indicator */}
        {loading && (
          <div className="flex justify-start message-appear">
            <div className="flex gap-2">
              <div className="flex-shrink-0 w-8 h-8 bg-campus-100 rounded-full flex items-center justify-center">
                <Bot className="w-4 h-4 text-campus-700" />
              </div>
              <div className="chat-bubble-bot flex items-center gap-1.5 py-4">
                <div className="typing-dot" style={{ animationDelay: '0ms' }} />
                <div className="typing-dot" style={{ animationDelay: '200ms' }} />
                <div className="typing-dot" style={{ animationDelay: '400ms' }} />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-cream-200 p-4 bg-white/50">
        <div className="flex gap-2">
          <input
            id="chat-input"
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask me anything about campus..."
            className="input-field flex-1"
            disabled={loading}
          />
          <button
            id="chat-send"
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="btn-primary px-4"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Tickets Tab ───────────────────────────────────────────

const RATING_LABELS = {
  1: '1/5 - Poor',
  2: '2/5 - Fair',
  3: '3/5 - Good',
  4: '4/5 - Very Good',
  5: '5/5 - Excellent!',
};

function TicketsTab({ initialTicketId }) {
  const [tickets, setTickets] = useState([]);
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [loading, setLoading] = useState(true);
  const [replyText, setReplyText] = useState('');
  const [sendingReply, setSendingReply] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createForm, setCreateForm] = useState({
    category: 'feedback',
    subject: '',
    description: '',
  });
  const [creating, setCreating] = useState(false);

  // Rating Modal state
  const [ratingModalTicket, setRatingModalTicket] = useState(null);
  const [ratingValue, setRatingValue] = useState(5);
  const [hoverRating, setHoverRating] = useState(0);
  const [ratingComment, setRatingComment] = useState('');
  const [submittingRating, setSubmittingRating] = useState(false);
  const [ratingSubmitted, setRatingSubmitted] = useState(false);
  const [dismissedTickets, setDismissedTickets] = useState(new Set());

  const { on } = useSocket();

  const openRatingModal = (ticket) => {
    setRatingModalTicket(ticket);
    setRatingValue(ticket.rating || 5);
    setHoverRating(0);
    setRatingComment(ticket.rating_comment || '');
    setRatingSubmitted(false);
  };

  const closeRatingModal = () => {
    if (ratingModalTicket) {
      setDismissedTickets(prev => new Set([...prev, ratingModalTicket.id]));
    }
    setRatingModalTicket(null);
    setRatingSubmitted(false);
    setRatingComment('');
    setRatingValue(5);
    setHoverRating(0);
  };

  const submitRating = async () => {
    if (!ratingModalTicket || !ratingValue || submittingRating) return;
    setSubmittingRating(true);
    try {
      const res = await api.post(`/tickets/${ratingModalTicket.id}/rate`, {
        rating: ratingValue,
        comment: ratingComment.trim() || undefined,
      });
      setRatingSubmitted(true);
      if (selectedTicket && selectedTicket.id === ratingModalTicket.id) {
        setSelectedTicket(res.data);
      }
      setTickets(prev => prev.map(t => t.id === ratingModalTicket.id ? { ...t, rating: res.data.rating, rating_comment: res.data.rating_comment, rated_at: res.data.rated_at } : t));
      setTimeout(() => {
        closeRatingModal();
      }, 2000);
    } catch (err) {
      console.error('Failed to submit rating:', err);
    } finally {
      setSubmittingRating(false);
    }
  };

  const handleCreateTicket = async (e) => {
    e.preventDefault();
    if (!createForm.subject.trim() || !createForm.description.trim() || creating) return;
    setCreating(true);
    try {
      const res = await api.post('/tickets', createForm);
      setCreateForm({ category: 'feedback', subject: '', description: '' });
      setShowCreateModal(false);
      await fetchTickets();
      if (res.data?.id) {
        await loadTicketDetail(res.data.id);
      }
    } catch (err) {
      console.error('Failed to create ticket:', err);
    } finally {
      setCreating(false);
    }
  };

  const fetchTickets = useCallback(async () => {
    try {
      const response = await api.get('/tickets');
      setTickets(response.data);
      return response.data;
    } catch (err) {
      console.error('Failed to fetch tickets:', err);
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  const loadTicketDetail = useCallback(async (ticketId, autoPrompt = true) => {
    try {
      const response = await api.get(`/tickets/${ticketId}`);
      setSelectedTicket(response.data);
      if (autoPrompt && response.data.status === 'resolved' && !response.data.rating && !dismissedTickets.has(response.data.id)) {
        openRatingModal(response.data);
      }
    } catch (err) {
      console.error('Failed to load ticket:', err);
    }
  }, [dismissedTickets]);

  useEffect(() => {
    fetchTickets().then((loaded) => {
      if (initialTicketId && loaded && loaded.length > 0) {
        const match = loaded.find(t => t.id === Number(initialTicketId) || t.tracking_id === initialTicketId);
        if (match) {
          loadTicketDetail(match.id, true);
        }
      }
    });

    const unsub1 = on('ticket:update', (data) => {
      fetchTickets().then((loaded) => {
        if (selectedTicket && data?.ticket_id === selectedTicket.id) {
          loadTicketDetail(selectedTicket.id, true);
        } else if (data?.ticket_id && data?.status === 'resolved' && !dismissedTickets.has(data.ticket_id)) {
          const match = (loaded || []).find(t => t.id === data.ticket_id);
          if (match && !match.rating) {
            openRatingModal(match);
          }
        }
      });
    });
    const unsub2 = on('ticket:message', () => {
      fetchTickets();
      if (selectedTicket) loadTicketDetail(selectedTicket.id, false);
    });
    return () => { unsub1(); unsub2(); };
  }, [fetchTickets, on, initialTicketId, selectedTicket, dismissedTickets, loadTicketDetail]);

  useEffect(() => {
    if (initialTicketId && tickets.length > 0) {
      const match = tickets.find(t => t.id === Number(initialTicketId) || t.tracking_id === initialTicketId);
      if (match) {
        loadTicketDetail(match.id, true);
      }
    }
  }, [initialTicketId, tickets, loadTicketDetail]);

  const sendReply = async () => {
    if (!replyText.trim() || !selectedTicket) return;
    setSendingReply(true);
    try {
      await api.post(`/tickets/${selectedTicket.id}/messages`, { message: replyText });
      setReplyText('');
      await loadTicketDetail(selectedTicket.id, false);
    } catch (err) {
      console.error('Failed to send reply:', err);
    } finally {
      setSendingReply(false);
    }
  };

  const getStatusBadge = (status) => {
    const cls = {
      open: 'badge-open',
      in_progress: 'badge-in-progress',
      resolved: 'badge-resolved',
    }[status] || 'badge-open';
    return <span className={cls}>{status.replace('_', ' ').toUpperCase()}</span>;
  };

  const getPriorityBadge = (priority) => {
    const cls = {
      critical: 'badge-critical',
      high: 'badge-high',
      medium: 'badge-medium',
      low: 'badge-low',
    }[priority] || 'badge-medium';
    return <span className={cls}>{priority.toUpperCase()}</span>;
  };

  const renderRatingModal = () => {
    if (!ratingModalTicket) return null;
    return (
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl border border-cream-200 animate-scale-in relative">
          <button
            onClick={closeRatingModal}
            className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 p-1.5 rounded-lg hover:bg-gray-100 transition-colors"
            title="Dismiss"
          >
            <X className="w-5 h-5" />
          </button>

          {ratingSubmitted ? (
            <div className="text-center py-6">
              <div className="w-14 h-14 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto mb-3">
                <CheckCircle2 className="w-8 h-8" />
              </div>
              <h3 className="font-display font-bold text-xl text-gray-900 mb-1">Thank You for Your Feedback!</h3>
              <p className="text-sm text-gray-600 mb-4">
                Your rating and review have been recorded. This helps recognize our agents and improve campus support.
              </p>
              <button
                onClick={closeRatingModal}
                className="btn-primary px-5 py-2 text-sm"
              >
                Close
              </button>
            </div>
          ) : (
            <div>
              <div className="text-center mb-5">
                <div className="w-12 h-12 bg-amber-100 text-amber-600 rounded-full flex items-center justify-center mx-auto mb-3">
                  <Star className="w-6 h-6 fill-amber-500 text-amber-500" />
                </div>
                <h3 className="font-display font-bold text-lg text-gray-900">Rate Your Support Experience</h3>
                <p className="text-xs text-gray-500 mt-1">
                  Ticket <span className="font-mono font-semibold text-campus-700">{ratingModalTicket.tracking_id}</span> has been solved by{' '}
                  <span className="font-semibold text-gray-700">{ratingModalTicket.assigned_agent_name || 'Campus Support'}</span>.
                </p>
                <p className="text-xs text-gray-600 mt-1 font-medium">
                  How effectively did the agent resolve your issue?
                </p>
              </div>

              {/* Star selector */}
              <div className="flex flex-col items-center justify-center mb-4">
                <div className="flex items-center gap-2">
                  {[1, 2, 3, 4, 5].map((star) => {
                    const active = (hoverRating || ratingValue) >= star;
                    return (
                      <button
                        key={star}
                        type="button"
                        onClick={() => setRatingValue(star)}
                        onMouseEnter={() => setHoverRating(star)}
                        onMouseLeave={() => setHoverRating(0)}
                        className="p-1 transition-transform hover:scale-125 focus:outline-none"
                      >
                        <Star
                          className={`w-8 h-8 transition-colors ${
                            active ? 'text-amber-400 fill-amber-400' : 'text-gray-300 stroke-gray-300'
                          }`}
                        />
                      </button>
                    );
                  })}
                </div>
                <span className="text-xs font-semibold text-campus-800 mt-2 h-4">
                  {RATING_LABELS[hoverRating || ratingValue] || ''}
                </span>
              </div>

              {/* Comment field */}
              <div className="mb-4">
                <label className="block text-xs font-semibold text-gray-600 mb-1">
                  Comments <span className="font-normal text-gray-400">(optional)</span>
                </label>
                <textarea
                  rows={3}
                  value={ratingComment}
                  onChange={(e) => setRatingComment(e.target.value)}
                  placeholder="Share details about the service you received..."
                  className="input-field text-sm"
                  maxLength={500}
                />
              </div>

              {/* Action buttons */}
              <div className="flex items-center justify-end gap-2 pt-2 border-t border-cream-200">
                <button
                  type="button"
                  onClick={closeRatingModal}
                  disabled={submittingRating}
                  className="btn-ghost text-xs py-2 px-3 text-gray-500 hover:text-gray-700"
                >
                  Skip
                </button>
                <button
                  type="button"
                  onClick={submitRating}
                  disabled={submittingRating || ratingValue < 1}
                  className="btn-primary text-xs py-2 px-4 flex items-center gap-1.5"
                >
                  {submittingRating ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" /> Submitting...
                    </>
                  ) : (
                    'Submit Rating'
                  )}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 text-campus-500 animate-spin" />
      </div>
    );
  }

  if (selectedTicket) {
    return (
      <div className="flex flex-col h-full relative">
        {/* Header */}
        <div className="p-4 border-b border-cream-200 bg-white/50">
          <button onClick={() => setSelectedTicket(null)} className="btn-ghost text-sm mb-2">
            ← Back to tickets
          </button>
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div>
              <div className="flex items-center gap-2 flex-wrap mb-1">
                <h3 className="font-display font-bold text-lg text-campus-700">{selectedTicket.tracking_id}</h3>
                {getStatusBadge(selectedTicket.status)}
                {getPriorityBadge(selectedTicket.priority)}
                {selectedTicket.rating && (
                  <span className="badge bg-amber-50 text-amber-800 border border-amber-200 text-xs font-semibold flex items-center gap-1">
                    <Star className="w-3 h-3 fill-amber-400 text-amber-400" /> {selectedTicket.rating}/5
                  </span>
                )}
                {selectedTicket.assigned_agent_name ? (
                  <span className="badge bg-blue-50 text-blue-700 border border-blue-200 text-xs">
                    👤 Agent: {selectedTicket.assigned_agent_name}
                  </span>
                ) : (
                  <span className="badge bg-amber-50 text-amber-700 border border-amber-200 text-xs">
                    ⏳ Unassigned
                  </span>
                )}
                {selectedTicket.queue_position && selectedTicket.status !== 'resolved' && (
                  <span className="badge bg-purple-50 text-purple-700 border border-purple-200 text-xs font-semibold">
                    🔢 Queue #{selectedTicket.queue_position} in line
                  </span>
                )}
              </div>
              <p className="text-sm font-medium text-gray-700">{selectedTicket.subject}</p>
            </div>
          </div>
        </div>

        {/* Timeline */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {/* Description */}
          <div className="bg-cream-100 rounded-xl p-4 text-sm">
            <p className="text-gray-500 text-xs mb-1">Original Description</p>
            <p className="text-gray-700">{selectedTicket.description}</p>
            <p className="text-xs text-gray-400 mt-2">
              <Clock className="w-3 h-3 inline mr-1" />
              {new Date(selectedTicket.created_at).toLocaleString()}
            </p>
          </div>

          {/* Messages */}
          {(selectedTicket.messages || []).map((msg) => (
            <div key={msg.id} className={`flex ${msg.sender_type === 'student' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] rounded-xl p-3 text-sm ${
                msg.sender_type === 'system'
                  ? 'bg-gray-100 text-gray-500 text-center w-full text-xs italic'
                  : msg.sender_type === 'student'
                    ? 'bg-campus-700 text-white'
                    : 'bg-white border border-cream-300'
              }`}>
                {msg.sender_type !== 'system' && (
                  <p className="text-xs font-semibold mb-1 opacity-70">{msg.sender_name || msg.sender_type}</p>
                )}
                <p>{msg.message}</p>
                <p className="text-[10px] opacity-50 mt-1">
                  {new Date(msg.timestamp).toLocaleString()}
                </p>
              </div>
            </div>
          ))}
        </div>

        {/* Resolved banner with Rating */}
        {selectedTicket.status === 'resolved' && (
          <div className="border-t border-cream-200 p-4 bg-amber-50/60 border-amber-100 flex items-center justify-between flex-wrap gap-3">
            <div>
              <div className="flex items-center gap-1.5 font-semibold text-sm text-gray-800">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                This ticket has been marked as resolved
              </div>
              {selectedTicket.rating ? (
                <div className="flex items-center gap-1.5 mt-1">
                  <span className="text-xs text-gray-600">Your Rating:</span>
                  <div className="flex items-center">
                    {[1, 2, 3, 4, 5].map((s) => (
                      <Star
                        key={s}
                        className={`w-3.5 h-3.5 ${s <= selectedTicket.rating ? 'text-amber-400 fill-amber-400' : 'text-gray-300'}`}
                      />
                    ))}
                  </div>
                  <span className="text-xs font-bold text-gray-700">{selectedTicket.rating}/5</span>
                  {selectedTicket.rating_comment && (
                    <span className="text-xs text-gray-500 italic ml-2">"{selectedTicket.rating_comment}"</span>
                  )}
                </div>
              ) : (
                <p className="text-xs text-gray-600 mt-0.5">
                  How was your support experience? Your feedback helps us improve.
                </p>
              )}
            </div>
            <button
              onClick={() => openRatingModal(selectedTicket)}
              className="btn-primary text-xs flex items-center gap-1.5 py-1.5 px-3 bg-amber-600 hover:bg-amber-700 text-white"
            >
              <Star className="w-3.5 h-3.5 fill-current" />
              {selectedTicket.rating ? 'Update Rating' : 'Rate Support Agent'}
            </button>
          </div>
        )}

        {/* Reply input */}
        {selectedTicket.status !== 'resolved' && (
          <div className="border-t border-cream-200 p-4 bg-white/50">
            <div className="flex gap-2">
              <input
                type="text"
                value={replyText}
                onChange={(e) => setReplyText(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && sendReply()}
                placeholder="Type a reply..."
                className="input-field flex-1"
              />
              <button onClick={sendReply} disabled={sendingReply || !replyText.trim()} className="btn-primary px-4">
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {renderRatingModal()}
      </div>
    );
  }

  return (
    <div className="p-4 space-y-3 overflow-y-auto h-full relative">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-display text-xl font-bold text-campus-700">My Tickets</h2>
        <button
          onClick={() => setShowCreateModal(true)}
          className="btn-primary text-xs flex items-center gap-1.5 px-3 py-2"
        >
          <Plus className="w-4 h-4" /> Create Ticket
        </button>
      </div>

      {tickets.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <Ticket className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p className="font-medium">No tickets yet</p>
          <p className="text-sm mt-1">Issues reported in chat or submitted here will appear in real time</p>
        </div>
      ) : (
        tickets.map((ticket) => (
          <button
            key={ticket.id}
            onClick={() => loadTicketDetail(ticket.id)}
            className="card w-full text-left p-4 flex items-center justify-between group"
          >
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1 flex-wrap">
                <span className="font-mono text-xs text-campus-600 font-semibold">{ticket.tracking_id}</span>
                {getStatusBadge(ticket.status)}
                {getPriorityBadge(ticket.priority)}
                {ticket.rating && (
                  <span className="badge bg-amber-50 text-amber-800 text-[10px] font-semibold border border-amber-200 flex items-center gap-1">
                    <Star className="w-2.5 h-2.5 fill-amber-400 text-amber-400" /> {ticket.rating}/5
                  </span>
                )}
                {ticket.assigned_agent_name && (
                  <span className="badge bg-blue-50 text-blue-700 text-[10px] border border-blue-200">
                    👤 {ticket.assigned_agent_name}
                  </span>
                )}
                {ticket.queue_position && ticket.status !== 'resolved' && (
                  <span className="badge bg-purple-50 text-purple-700 text-[10px] font-semibold border border-purple-200">
                    🔢 #{ticket.queue_position} in line
                  </span>
                )}
                <span className="text-[11px] text-gray-400">
                  {TICKET_CATEGORY_LABELS[ticket.category] || ticket.category}
                </span>
              </div>
              <p className="text-sm font-medium text-gray-800 truncate">{ticket.subject}</p>
              <p className="text-xs text-gray-400 mt-1">
                {new Date(ticket.created_at).toLocaleDateString()}
              </p>
            </div>
            <ChevronRight className="w-4 h-4 text-gray-300 group-hover:text-campus-500 transition-colors" />
          </button>
        ))
      )}

      {/* Create Ticket Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl border border-cream-200 animate-scale-in">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-display font-bold text-lg text-campus-800">Create New Ticket</h3>
              <button onClick={() => setShowCreateModal(false)} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateTicket} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-600 uppercase mb-1">Category</label>
                <select
                  value={createForm.category}
                  onChange={(e) => setCreateForm(prev => ({ ...prev, category: e.target.value }))}
                  className="input-field"
                >
                  {Object.entries(TICKET_CATEGORY_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-600 uppercase mb-1">Subject</label>
                <input
                  type="text"
                  required
                  value={createForm.subject}
                  onChange={(e) => setCreateForm(prev => ({ ...prev, subject: e.target.value }))}
                  placeholder="Brief summary of your request or feedback"
                  className="input-field"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-600 uppercase mb-1">Description</label>
                <textarea
                  required
                  rows={4}
                  value={createForm.description}
                  onChange={(e) => setCreateForm(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="Provide complete details..."
                  className="input-field"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="btn-ghost text-sm"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="btn-primary text-sm flex items-center gap-2"
                >
                  {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Submit Ticket'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {renderRatingModal()}
    </div>
  );
}

// ─── Navigation Tab ─────────────────────────────────────────

function NavigationTab({ initialScene, initialName }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [selectedNode, setSelectedNode] = useState(initialName ? { name: initialName, panoee_scene_id: initialScene } : null);
  const [searching, setSearching] = useState(false);
  const [panoeeUrl, setPanoeeUrl] = useState('');
  const [loadingTour, setLoadingTour] = useState(true);

  useEffect(() => {
    // Fetch active tour configured by administration
    const normalizeTourUrl = (raw) => {
      if (!raw) return '';
      const trimmed = raw.trim();
      // Extract src from <iframe> embed code if pasted
      const iframeSrcMatch = trimmed.match(/src=["']([^"']+)["']/i);
      if (iframeSrcMatch) {
        const extracted = iframeSrcMatch[1].trim();
        return extracted.startsWith('http') ? extracted : `https://${extracted}`;
      }
      // Add https:// if no protocol
      if (!/^https?:\/\//i.test(trimmed)) return `https://${trimmed}`;
      return trimmed;
    };

    const fetchTour = async () => {
      try {
        const res = await api.get('/navigation/tour');
        if (res.data?.tour_url) {
          setPanoeeUrl(normalizeTourUrl(res.data.tour_url));
        }
      } catch (err) {
        console.error('Failed to load campus tour:', err);
      } finally {
        setLoadingTour(false);
      }
    };
    fetchTour();
  }, []);

  useEffect(() => {
    if (initialScene && initialName) {
      setSelectedNode({ name: initialName, panoee_scene_id: initialScene });
    }
  }, [initialScene, initialName]);

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const response = await api.get(`/navigation/search?q=${encodeURIComponent(searchQuery)}`);
      setSearchResults(response.data);
    } catch (err) {
      console.error('Search failed:', err);
    } finally {
      setSearching(false);
    }
  };

  const selectLocation = (node) => {
    setSelectedNode(node);
    setSearchResults([]);
    setSearchQuery('');
  };

  return (
    <div className="flex flex-col h-full relative">
      {/* Search & Tour Toolbar */}
      <div className="p-4 border-b border-cream-200 bg-white/70 backdrop-blur-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="font-display text-xl font-bold text-campus-700">Campus Map & Virtual Tour</h2>
          <p className="text-xs text-gray-500">Search database locations or explore the 360° virtual tour</p>
        </div>
      </div>

      {/* Location Search Bar */}
      <div className="p-4 bg-white/40 border-b border-cream-200">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              id="nav-search"
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Search for campus buildings, offices, or labs..."
              className="input-field pl-10"
            />
          </div>
          <button onClick={handleSearch} disabled={searching} className="btn-primary px-4">
            {searching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
          </button>
        </div>

        {/* Search results dropdown */}
        {searchResults.length > 0 && (
          <div className="mt-2 bg-white rounded-xl shadow-card border border-cream-200 overflow-hidden">
            {searchResults.map((node) => (
              <button
                key={node.id}
                onClick={() => selectLocation(node)}
                className="w-full text-left px-4 py-3 hover:bg-campus-50 transition-colors border-b border-cream-100 last:border-0"
              >
                <div className="flex items-center gap-3">
                  <MapPin className="w-4 h-4 text-campus-500 flex-shrink-0" />
                  <div>
                    <p className="text-sm font-medium text-gray-800">{node.name}</p>
                    <p className="text-xs text-gray-400">
                      {node.building}{node.floor ? ` • ${node.floor}` : ''}
                    </p>
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Selected location info banner */}
      {selectedNode && (
        <div className="px-4 py-3 bg-campus-50 border-b border-campus-200 animate-fade-in flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <MapPin className="w-4 h-4 text-campus-600" />
              <span className="text-sm font-semibold text-campus-800">{selectedNode.name}</span>
              {selectedNode.building && (
                <span className="text-xs bg-campus-100 text-campus-700 px-2 py-0.5 rounded-full font-medium">
                  {selectedNode.building}{selectedNode.floor ? ` • Floor ${selectedNode.floor}` : ''}
                </span>
              )}
            </div>
            {selectedNode.description && (
              <p className="text-xs text-gray-600 mt-1 ml-6">{selectedNode.description}</p>
            )}
            <p className="text-[11px] text-campus-700/90 mt-1.5 ml-6 font-medium">
              💡 <b>Floorplan Wayfinding:</b> Use the floorplan pins and hotspots inside the 360° tour to navigate to this location.
            </p>
          </div>
          <button
            onClick={() => setSelectedNode(null)}
            className="text-xs text-gray-400 hover:text-gray-600 ml-2"
          >
            ✕ Dismiss
          </button>
        </div>
      )}

      {/* Tour Display or Thoughtful Student-Facing Empty State */}
      {loadingTour ? (
        <div className="flex-1 flex items-center justify-center p-6 bg-cream-50">
          <Loader2 className="w-8 h-8 text-campus-500 animate-spin" />
        </div>
      ) : panoeeUrl ? (
        <div className="flex-1 bg-gray-900 relative">
          <iframe
            src={panoeeUrl}
            width="100%"
            height="100%"
            frameBorder="0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; xr-spatial-tracking"
            allowFullScreen
            title="Campus Virtual Tour"
            className="absolute inset-0 w-full h-full border-0"
          />
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center p-6 bg-cream-50 overflow-y-auto">
          <div className="max-w-md w-full bg-white rounded-3xl shadow-card border border-cream-200 p-8 text-center animate-slide-up">
            <div className="w-16 h-16 bg-campus-50 rounded-2xl flex items-center justify-center mx-auto mb-4 border border-campus-200 shadow-sm">
              <Compass className="w-8 h-8 text-campus-600" />
            </div>
            <h3 className="font-display text-xl font-bold text-campus-800 mb-2">360° Virtual Tour Coming Soon</h3>
            <p className="text-gray-600 text-sm mb-6 leading-relaxed">
              The university's interactive 360° campus tour is currently being calibrated and updated by administration.
            </p>
            <div className="bg-campus-50/70 border border-campus-100 rounded-xl p-4 text-left space-y-2">
              <p className="text-xs font-semibold text-campus-800">🔍 In the meantime, you can:</p>
              <ul className="text-xs text-campus-700 space-y-1 pl-3 list-disc">
                <li>Search any lecture hall, lab, or office in the search bar above.</li>
                <li>Find exact buildings and floor locations instantly.</li>
                <li>Ask Chana in the Chat tab for room and facility details.</li>
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Main Student Dashboard ────────────────────────────────

export default function StudentDashboard() {
  const { user, logout } = useAuth();
  const [activeTab, setActiveTab] = useState('chat');
  const [navScene, setNavScene] = useState(null);
  const [navName, setNavName] = useState(null);
  const [ticketToOpen, setTicketToOpen] = useState(null);

  // Persistent chat state across tab switches and component mounts
  const [chatMessages, setChatMessages] = useState([]);
  const [chatSessionId, setChatSessionId] = useState(null);

  const handleNavigate = (targetTab, targetArg, extraName) => {
    if (targetTab === 'tickets') {
      setTicketToOpen(targetArg || null);
      setActiveTab('tickets');
      return;
    }
    if (targetTab === 'navigation') {
      setNavScene(targetArg || null);
      setNavName(extraName || null);
      setActiveTab('navigation');
      return;
    }
    setActiveTab(targetTab);
  };

  const tabs = [
    { id: 'chat', label: 'Chat', icon: MessageSquare },
    { id: 'tickets', label: 'My Tickets', icon: Ticket },
    { id: 'navigation', label: 'Campus Map', icon: Map },
  ];

  return (
    <div className="flex flex-col h-screen bg-cream-100">
      {/* Top Navbar */}
      <header className="bg-white/80 backdrop-blur-xl border-b border-cream-200 px-4 py-3 flex items-center justify-between z-20">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-gradient-to-br from-campus-700 to-campus-500 rounded-xl flex items-center justify-center">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="font-display text-lg font-bold text-campus-700 leading-tight">Chana</h1>
            <p className="text-[11px] text-gray-400 leading-tight">Chatbot & Navigation System</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-600 hidden sm:block">Hi, {user?.name?.split(' ')[0]}</span>
          <button onClick={logout} className="btn-ghost text-sm flex items-center gap-1.5 text-red-500 hover:bg-red-50">
            <LogOut className="w-4 h-4" /> Logout
          </button>
        </div>
      </header>

      {/* Tab Navigation */}
      <div className="bg-white/60 backdrop-blur-sm border-b border-cream-200 px-4">
        <div className="flex gap-1">
          {tabs.map(tab => (
            <button
              key={tab.id}
              id={`tab-${tab.id}`}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-all duration-200 border-b-2 ${
                activeTab === tab.id
                  ? 'border-campus-600 text-campus-700'
                  : 'border-transparent text-gray-400 hover:text-gray-600'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'chat' && (
          <ChatTab
            onNavigate={handleNavigate}
            messages={chatMessages}
            setMessages={setChatMessages}
            sessionId={chatSessionId}
            setSessionId={setChatSessionId}
          />
        )}
        {activeTab === 'tickets' && (
          <TicketsTab initialTicketId={ticketToOpen} />
        )}
        {activeTab === 'navigation' && (
          <NavigationTab initialScene={navScene} initialName={navName} />
        )}
      </div>
    </div>
  );
}
