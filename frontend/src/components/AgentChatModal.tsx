'use client';

import { useState } from 'react';
import { askAgent } from '@/lib/api';

export function AgentChatModal() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Array<{ sender: 'user' | 'agent'; text: string; time: string }>>([
    {
      sender: 'agent',
      text: 'Greetings! I am the Chief Investment Officer for AI Trader Agent. Ask me anything about our live portfolio strategy, Nifty 50 risk posture, or current trade rationale.',
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userText = input.trim();
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    
    setMessages((prev) => [...prev, { sender: 'user', text: userText, time: timeStr }]);
    setInput('');
    setLoading(true);

    try {
      const reply = await askAgent(userText);
      const agentTimeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      setMessages((prev) => [...prev, { sender: 'agent', text: reply, time: agentTimeStr }]);
    } catch {
      setMessages((prev) => [...prev, { sender: 'agent', text: 'Apologies, I encountered a temporary connection issue. Please try again.', time: timeStr }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 z-40 flex items-center gap-2 rounded-full border border-profit/50 bg-panel px-5 py-3 text-sm font-bold text-profit shadow-glow backdrop-blur transition hover:scale-105 hover:bg-profit/10"
      >
        <span className="relative flex h-3 w-3">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-profit opacity-75"></span>
          <span className="relative inline-flex h-3 w-3 rounded-full bg-profit"></span>
        </span>
        Interact with AI Fund Manager
      </button>

      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm">
          <div className="flex h-[580px] w-full max-w-xl flex-col rounded-2xl border border-grid bg-panel p-5 shadow-2xl">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-grid pb-4">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-profit/40 bg-profit/10 font-bold text-profit">
                  AI
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-100">Hedge Fund Agent Desk</h3>
                  <p className="text-xs text-profit">CIO · Risk Officer · Technical Analyst</p>
                </div>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="rounded-lg p-2 text-slate-400 hover:bg-grid hover:text-slate-100"
              >
                ✕
              </button>
            </div>

            {/* Chat Body */}
            <div className="my-4 flex-1 overflow-y-auto space-y-4 pr-2 text-sm">
              {messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}
                >
                  <div
                    className={`max-w-[85%] rounded-2xl p-4 text-sm leading-relaxed ${
                      msg.sender === 'user'
                        ? 'border border-profit/30 bg-profit/10 text-slate-100'
                        : 'border border-grid bg-terminal/90 text-slate-200'
                    }`}
                  >
                    <p>{msg.text}</p>
                  </div>
                  <span className="mt-1 text-[10px] text-slate-500">{msg.time}</span>
                </div>
              ))}
              {loading && (
                <div className="flex items-center gap-2 text-xs text-profit">
                  <span className="animate-pulse">Agent reasoning in progress...</span>
                </div>
              )}
            </div>

            {/* Quick Prompts */}
            <div className="mb-3 flex flex-wrap gap-2">
              {['Why Reliance?', 'What is our Risk Level?', 'How do we beat Nifty?'].map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => setInput(prompt)}
                  className="rounded-full border border-grid bg-terminal/60 px-3 py-1 text-xs text-slate-300 hover:border-profit/40 hover:text-profit"
                >
                  {prompt}
                </button>
              ))}
            </div>

            {/* Input Form */}
            <form onSubmit={handleSend} className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask the AI Fund Manager..."
                className="flex-1 rounded-xl border border-grid bg-terminal px-4 py-2.5 text-sm text-slate-100 focus:border-profit focus:outline-none"
              />
              <button
                type="submit"
                disabled={loading || !input.trim()}
                className="rounded-xl border border-profit/40 bg-profit/20 px-5 py-2.5 text-sm font-semibold text-profit transition hover:bg-profit/30 disabled:opacity-50"
              >
                Send
              </button>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
