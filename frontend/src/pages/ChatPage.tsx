// --- Ajan: INSAATCI (THE CONSTRUCTOR) ---
// AI Chat sayfası: TonbilAi dogal dil asistani arayuzu
// ChatGPT benzeri modern sohbet arayuzu, cyberpunk/glassmorphism tema

import { useEffect, useRef, useState, useCallback, KeyboardEvent } from 'react';
import {
  Brain,
  Bot,
  User,
  SendHorizonal,
  Trash2,
  ChevronDown,
  ChevronRight,
  Shield,
  Terminal,
  Sparkles,
  Zap,
  MessageSquare,
} from 'lucide-react';
import { GlassCard } from '../components/common/GlassCard';
import { MarkdownRenderer } from '../components/chat/MarkdownRenderer';
import {
  sendChatMessage,
  fetchChatHistory,
  clearChatHistory,
  type ChatMessage,
  type ChatSendResponse,
} from '../services/chatApi';

// --- Yerel Mesaj Tipi (UI için genisletilmis) ---
interface LocalMessage {
  id: number | string;
  role: 'user' | 'assistant';
  content: string;
  action_type: string | null;
  action_result: Record<string, unknown> | null;
  timestamp: string;
}

// --- Oneri Cip Verileri ---
const SUGGESTION_CHIPS = [
  { label: 'Sistem durumu', icon: Terminal },
  { label: 'Bagli cihazlari goster', icon: Zap },
  { label: 'Facebook ve Youtube engelle', icon: Shield },
  { label: 'Yardim', icon: MessageSquare },
];

// --- Ornek Komutlar (Bos Durum) ---
const EXAMPLE_COMMANDS = [
  'Facebook, Instagram ve TikTok engelle',
  'Babamin telefonunu engelle',
  'Kumar sitelerini engelle',
  'Sistem durumu',
  'Almanya VPN baglan',
  'Bagli cihazlari goster',
];

// --- Yardimci: Zaman Formati ---
function formatTimestamp(ts: string): string {
  try {
    const date = new Date(ts);
    return date.toLocaleTimeString('tr-TR', {
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '';
  }
}

// --- JSON Syntax Highlight (XSS-güvenli, dangerouslySetInnerHTML YOK) ---
function SyntaxHighlightedJson({ data }: { data: Record<string, unknown> }) {
  const jsonStr = JSON.stringify(data, null, 2);

  // Her satiri React elementleri ile isle (XSS-güvenli)
  const lines = jsonStr.split('\n').map((line, i) => {
    const segments: React.ReactNode[] = [];
    let remaining = line;
    let segIdx = 0;

    // Anahtar + deger parcalama
    const keyValMatch = remaining.match(/^(\s*)"([^"]+)":\s*/);
    if (keyValMatch) {
      const [fullMatch, indent, key] = keyValMatch;
      segments.push(<span key={segIdx++}>{indent}</span>);
      segments.push(<span key={segIdx++} className="text-neon-cyan">"{key}"</span>);
      segments.push(<span key={segIdx++}>: </span>);
      remaining = remaining.slice(fullMatch.length);

      // Deger tipi renklendirme
      const strMatch = remaining.match(/^"([^"]*)"(,?)$/);
      const numMatch = remaining.match(/^(\d+\.?\d*)(,?)$/);
      const boolMatch = remaining.match(/^(true|false|null)(,?)$/);

      if (strMatch) {
        segments.push(<span key={segIdx++} className="text-neon-green">"{strMatch[1]}"</span>);
        if (strMatch[2]) segments.push(<span key={segIdx++}>{strMatch[2]}</span>);
      } else if (numMatch) {
        segments.push(<span key={segIdx++} className="text-neon-amber">{numMatch[1]}</span>);
        if (numMatch[2]) segments.push(<span key={segIdx++}>{numMatch[2]}</span>);
      } else if (boolMatch) {
        segments.push(<span key={segIdx++} className="text-neon-magenta">{boolMatch[1]}</span>);
        if (boolMatch[2]) segments.push(<span key={segIdx++}>{boolMatch[2]}</span>);
      } else {
        segments.push(<span key={segIdx++}>{remaining}</span>);
      }
    } else {
      segments.push(<span key={segIdx++}>{line}</span>);
    }

    return <div key={i}>{segments}</div>;
  });

  return (
    <pre className="font-mono text-xs leading-relaxed overflow-x-auto whitespace-pre">
      {lines}
    </pre>
  );
}

// --- İşlem Sonuçu Karti (Collapsible) ---
function ActionResultCard({ actionType, actionResult }: {
  actionType: string | null;
  actionResult: Record<string, unknown> | null;
}) {
  const [expanded, setExpanded] = useState(false);

  if (!actionResult) return null;

  return (
    <div className="mt-3 rounded-xl border border-neon-green/20 bg-neon-green/5 overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-4 py-2.5 text-left hover:bg-neon-green/10 transition-colors"
      >
        {expanded ? (
          <ChevronDown size={14} className="text-neon-green flex-shrink-0" />
        ) : (
          <ChevronRight size={14} className="text-neon-green flex-shrink-0" />
        )}
        <Terminal size={14} className="text-neon-green flex-shrink-0" />
        <span className="text-xs font-semibold text-neon-green">
          İşlem Sonuçu
        </span>
        {actionType && (
          <span className="ml-auto text-xs text-gray-500 font-mono">
            {actionType}
          </span>
        )}
      </button>
      {expanded && (
        <div className="px-4 pb-3 border-t border-neon-green/10">
          <div className="mt-2 p-3 rounded-lg bg-surface-900/80">
            <SyntaxHighlightedJson data={actionResult} />
          </div>
        </div>
      )}
    </div>
  );
}

// --- Yazma Göstergesi (Typing Indicator) ---
function TypingIndicator() {
  return (
    <div className="flex items-start gap-3 max-w-[85%]">
      {/* Asistan Avatari */}
      <div className="flex-shrink-0 w-9 h-9 rounded-xl bg-neon-magenta/10 border border-neon-magenta/30 flex items-center justify-center">
        <Bot size={18} className="text-neon-magenta" />
      </div>
      {/* Yaziyor Animasyonu */}
      <div className="glass-card px-5 py-4 rounded-2xl rounded-tl-sm border-neon-magenta/20">
        <div className="flex items-center gap-1.5">
          <div
            className="w-2 h-2 rounded-full bg-neon-magenta animate-bounce"
            style={{ animationDelay: '0ms', animationDuration: '1s' }}
          />
          <div
            className="w-2 h-2 rounded-full bg-neon-magenta animate-bounce"
            style={{ animationDelay: '200ms', animationDuration: '1s' }}
          />
          <div
            className="w-2 h-2 rounded-full bg-neon-magenta animate-bounce"
            style={{ animationDelay: '400ms', animationDuration: '1s' }}
          />
          <span className="text-xs text-gray-500 ml-2">Dusunuyor...</span>
        </div>
      </div>
    </div>
  );
}

// --- Tek Mesaj Bileseni ---
function ChatBubble({ message }: { message: LocalMessage }) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex items-start gap-3 ${isUser ? 'flex-row-reverse' : ''} max-w-[85%] ${isUser ? 'ml-auto' : 'mr-auto'}`}>
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-9 h-9 rounded-xl flex items-center justify-center border ${
          isUser
            ? 'bg-neon-cyan/10 border-neon-cyan/30'
            : 'bg-neon-magenta/10 border-neon-magenta/30'
        }`}
      >
        {isUser ? (
          <User size={18} className="text-neon-cyan" />
        ) : (
          <Bot size={18} className="text-neon-magenta" />
        )}
      </div>

      {/* Mesaj Icerigi */}
      <div className="flex flex-col gap-1 min-w-0">
        <div
          className={`glass-card px-4 py-3 rounded-2xl ${
            isUser
              ? 'rounded-tr-sm border-neon-cyan/20 bg-neon-cyan/5'
              : 'rounded-tl-sm border-neon-magenta/20 bg-neon-magenta/5'
          }`}
        >
          {/* Mesaj Metni */}
          {isUser ? (
            <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">
              {message.content}
            </p>
          ) : (
            <div className="text-sm leading-relaxed break-words">
              <MarkdownRenderer text={message.content} />
            </div>
          )}

          {/* İşlem Sonuçu */}
          {!isUser && message.action_result && (
            <ActionResultCard
              actionType={message.action_type}
              actionResult={message.action_result}
            />
          )}
        </div>

        {/* Zaman Damgasi */}
        <span className={`text-[10px] text-gray-600 px-2 ${isUser ? 'text-right' : 'text-left'}`}>
          {formatTimestamp(message.timestamp)}
        </span>
      </div>
    </div>
  );
}

// --- Bos Durum Karsilama ---
function WelcomeEmptyState({ onCommandClick }: { onCommandClick: (cmd: string) => void }) {
  return (
    <div className="flex-1 flex items-center justify-center p-6">
      <div className="max-w-lg w-full text-center space-y-8">
        {/* Logo & Baslik */}
        <div className="space-y-4">
          <div className="mx-auto w-20 h-20 rounded-2xl bg-gradient-to-br from-neon-cyan/20 to-neon-magenta/20 border border-glass-border flex items-center justify-center shadow-neon">
            <Brain size={40} className="text-neon-cyan" />
          </div>
          <div>
            <h3 className="text-2xl font-bold neon-text">TonbilAi Asistan</h3>
            <p className="text-gray-400 text-sm mt-2">
              Router'inizi dogal dille yonetin. Asagidaki komutlari deneyin:
            </p>
          </div>
        </div>

        {/* Ornek Komutlar */}
        <GlassCard className="text-left">
          <div className="flex items-center gap-2 mb-4">
            <Sparkles size={16} className="text-neon-amber" />
            <span className="text-sm font-semibold text-gray-300">Ornek Komutlar</span>
          </div>
          <div className="space-y-2">
            {EXAMPLE_COMMANDS.map((cmd) => (
              <button
                key={cmd}
                onClick={() => onCommandClick(cmd)}
                className="w-full text-left px-4 py-2.5 rounded-xl text-sm text-gray-300
                           hover:text-neon-cyan hover:bg-neon-cyan/5 border border-transparent
                           hover:border-neon-cyan/20 transition-all duration-200 flex items-center gap-3 group"
              >
                <Terminal size={14} className="text-gray-600 group-hover:text-neon-cyan flex-shrink-0" />
                <span className="font-mono text-xs">{cmd}</span>
                <ChevronRight size={14} className="ml-auto text-gray-700 group-hover:text-neon-cyan opacity-0 group-hover:opacity-100 transition-opacity" />
              </button>
            ))}
          </div>
        </GlassCard>
      </div>
    </div>
  );
}

// =====================================================================
// ANA BILEŞEN: ChatPage
// =====================================================================
export function ChatPage() {
  // --- State ---
  const [messages, setMessages] = useState<LocalMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isHistoryLoading, setIsHistoryLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // --- Referanslar ---
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);

  // --- Otomatik scroll ---
  const scrollToBottom = useCallback(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading, scrollToBottom]);

  // --- Sohbet gecmisini yukle ---
  useEffect(() => {
    let cancelled = false;

    async function loadHistory() {
      try {
        setIsHistoryLoading(true);
        const history = await fetchChatHistory(50);
        if (!cancelled) {
          setMessages(history);
        }
      } catch (err) {
        console.error('Sohbet gecmisi yüklenemedi:', err);
        if (!cancelled) {
          setError('Sohbet gecmisi yüklenemedi.');
        }
      } finally {
        if (!cancelled) {
          setIsHistoryLoading(false);
        }
      }
    }

    loadHistory();
    return () => { cancelled = true; };
  }, []);

  // --- Textarea yukseklik ayari ---
  const adjustTextareaHeight = useCallback(() => {
    const ta = textareaRef.current;
    if (ta) {
      ta.style.height = 'auto';
      ta.style.height = `${Math.min(ta.scrollHeight, 160)}px`;
    }
  }, []);

  useEffect(() => {
    adjustTextareaHeight();
  }, [input, adjustTextareaHeight]);

  // --- Mesaj gönderme ---
  const handleSend = useCallback(async (messageText?: string) => {
    const text = (messageText ?? input).trim();
    if (!text || isLoading) return;

    setError(null);
    setInput('');

    // Kullanıcı mesajini ekle
    const userMsg: LocalMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text,
      action_type: null,
      action_result: null,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const response: ChatSendResponse = await sendChatMessage(text);

      // Asistan yanitini ekle
      const assistantMsg: LocalMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: response.reply,
        action_type: response.action_type,
        action_result: response.action_result,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      console.error('Mesaj gönderilemedi:', err);
      const errorText =
        err?.response?.data?.detail ??
        err?.message ??
        'Bilinmeyen bir hata oluştu.';

      // Hata mesajini asistan olarak ekle
      const errorMsg: LocalMessage = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: `Hata: ${errorText}`,
        action_type: null,
        action_result: null,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
      // Input'a tekrar odaklan
      setTimeout(() => textareaRef.current?.focus(), 100);
    }
  }, [input, isLoading]);

  // --- Gecmisi temizle ---
  const handleClearHistory = useCallback(async () => {
    if (isLoading) return;

    try {
      await clearChatHistory();
      setMessages([]);
      setError(null);
    } catch (err) {
      console.error('Gecmis temizlenemedi:', err);
      setError('Sohbet gecmisi temizlenemedi.');
    }
  }, [isLoading]);

  // --- Klavye yönetimi ---
  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      // Enter: gönder, Shift+Enter: yeni satir
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  // --- Oneri cipi tiklama ---
  const handleChipClick = useCallback(
    (text: string) => {
      handleSend(text);
    },
    [handleSend]
  );

  // --- Ornek komut tiklama (bos durum) ---
  const handleExampleClick = useCallback(
    (cmd: string) => {
      handleSend(cmd);
    },
    [handleSend]
  );

  // --- Yukleme durumu ---
  if (isHistoryLoading) {
    return (
      <div className="h-full flex flex-col">
        {/* Header */}
        <ChatHeader onClear={handleClearHistory} isLoading={true} />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center space-y-4">
            <div className="relative w-12 h-12 mx-auto">
              <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-neon-cyan animate-spin" />
              <div className="absolute inset-2 rounded-full border-2 border-transparent border-t-neon-magenta animate-spin" style={{ animationDirection: 'reverse', animationDuration: '0.8s' }} />
              <div className="absolute inset-4 rounded-full bg-neon-cyan/20 animate-pulse-neon" />
            </div>
            <p className="text-sm text-gray-500">Sohbet gecmisi yukleniyor...</p>
          </div>
        </div>
      </div>
    );
  }

  // --- Ana Render ---
  return (
    <div className="h-[calc(100vh-2rem)] flex flex-col">
      {/* Sayfa Baslik */}
      <ChatHeader onClear={handleClearHistory} isLoading={isLoading} />

      {/* Hata Bildirimi */}
      {error && (
        <div className="mx-0 mb-3 px-4 py-2.5 rounded-xl bg-neon-red/10 border border-neon-red/20 text-sm text-neon-red flex items-center gap-2">
          <Shield size={14} />
          <span>{error}</span>
          <button
            onClick={() => setError(null)}
            className="ml-auto text-neon-red/60 hover:text-neon-red text-xs"
          >
            Kapat
          </button>
        </div>
      )}

      {/* Chat Alan */}
      {messages.length === 0 && !isLoading ? (
        <WelcomeEmptyState onCommandClick={handleExampleClick} />
      ) : (
        <div
          ref={chatContainerRef}
          className="flex-1 overflow-y-auto px-2 py-4 space-y-5 scrollbar-thin"
        >
          {messages.map((msg) => (
            <ChatBubble key={msg.id} message={msg} />
          ))}

          {/* Yazma Göstergesi */}
          {isLoading && <TypingIndicator />}

          {/* Scroll Referansi */}
          <div ref={messagesEndRef} />
        </div>
      )}

      {/* Alt Kisim: Oneriler + Input */}
      <div className="flex-shrink-0 pt-2 pb-2 space-y-3">
        {/* Oneri Cipleri */}
        {!isLoading && (
          <div className="flex flex-wrap gap-2 px-1">
            {SUGGESTION_CHIPS.map((chip) => (
              <button
                key={chip.label}
                onClick={() => handleChipClick(chip.label)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs
                           border border-glass-border bg-glass hover:bg-glass-light
                           hover:border-neon-cyan/30 text-gray-400 hover:text-neon-cyan
                           transition-all duration-200 group"
              >
                <chip.icon size={12} className="group-hover:text-neon-cyan" />
                <span>{chip.label}</span>
              </button>
            ))}
          </div>
        )}

        {/* Mesaj Girişi */}
        <div className="glass-card p-2 rounded-2xl flex items-end gap-2 border-glass-border hover:border-neon-cyan/20 transition-colors">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Bir komut veya soru yazin..."
            rows={1}
            disabled={isLoading}
            className="flex-1 bg-transparent text-sm text-white placeholder-gray-600
                       resize-none outline-none px-3 py-2.5 max-h-40
                       scrollbar-thin disabled:opacity-50"
          />
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || isLoading}
            className="flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center
                       transition-all duration-200
                       disabled:opacity-30 disabled:cursor-not-allowed
                       enabled:bg-neon-cyan/10 enabled:hover:bg-neon-cyan/20
                       enabled:text-neon-cyan enabled:hover:shadow-neon
                       enabled:border enabled:border-neon-cyan/30"
          >
            <SendHorizonal size={18} />
          </button>
        </div>

        {/* Alt Bilgi */}
        <p className="text-center text-[10px] text-gray-700">
          TonbilAi Asistan - Router'inizi dogal dille yonetin
        </p>
      </div>
    </div>
  );
}

// --- Sayfa Basligi Bileseni ---
function ChatHeader({ onClear, isLoading }: { onClear: () => void; isLoading: boolean }) {
  return (
    <header className="flex items-center justify-between mb-4 flex-shrink-0">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-neon-cyan/20 to-neon-magenta/20 border border-glass-border flex items-center justify-center">
          <Brain size={22} className="text-neon-cyan" />
        </div>
        <div>
          <h2 className="text-xl font-bold neon-text">AI Asistan</h2>
          <p className="text-xs text-gray-500">
            TonbilAi Router'inizi dogal dille yonetin
          </p>
        </div>
      </div>

      <button
        onClick={onClear}
        disabled={isLoading}
        className="flex items-center gap-2 px-3 py-2 rounded-xl text-xs
                   border border-glass-border bg-glass hover:bg-neon-red/10
                   hover:border-neon-red/30 text-gray-400 hover:text-neon-red
                   transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed"
      >
        <Trash2 size={14} />
        <span>Gecmisi Temizle</span>
      </button>
    </header>
  );
}
