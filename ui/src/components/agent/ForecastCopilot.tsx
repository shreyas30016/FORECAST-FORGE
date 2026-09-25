"use client";

import React, { useState, useRef, useEffect } from "react";
import { Bot, X, Send, Loader2, Sparkles } from "lucide-react";
import { api } from "@/lib/api";
import { DecisionTraceDrawer } from "@/components/shared/DecisionTraceDrawer";

interface CopilotProps {
  context?: {
    page?: string;
    location?: string;
    latitude?: number;
    longitude?: number;
    lead_time_hours?: number;
    variable?: string;
    active_overlay?: string;
    trace_id?: string;
    replay_id?: string;
    selected_model?: string;
    valid_time?: string;
  };
}

interface Message {
  role: "user" | "assistant" | "system";
  content: string;
}

export function ForecastCopilot({ context }: CopilotProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [currentTool, setCurrentTool] = useState<string | null>(null);
  
  const [traceOpen, setTraceOpen] = useState(false);

  const endOfMessagesRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, currentTool]);

  const handleSend = async (text: string) => {
    if (!text.trim()) return;
    
    const newMessages: Message[] = [...messages, { role: "user", content: text }];
    setMessages(newMessages);
    setInput("");
    setIsLoading(true);
    setCurrentTool(null);

    try {
      const response = await api.postAgentChat({
        messages: newMessages,
        context: context
      });
      
      if (response.tool_activity && response.tool_activity.length > 0) {
        // Just flash the last tool briefly before showing the message
        const lastTool = response.tool_activity[response.tool_activity.length - 1];
        setCurrentTool(lastTool.tool.replace(/_/g, " "));
        
        setTimeout(() => {
          setCurrentTool(null);
          setMessages([...newMessages, { role: "assistant", content: response.response }]);
        }, 800);
      } else {
        setMessages([...newMessages, { role: "assistant", content: response.response }]);
      }
      
    } catch {
      setMessages([...newMessages, { role: "assistant", content: "I encountered an error connecting to my neural core. Please try again." }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      {/* Floating Orb Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-6 right-6 z-[9999] p-4 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-xl hover:shadow-indigo-500/25 hover:scale-105 transition-all flex items-center justify-center group"
          title="Forecast Copilot"
        >
          <Bot className="w-6 h-6 group-hover:animate-pulse" />
        </button>
      )}

      {/* Slide-out Drawer */}
      <div 
        className={`fixed inset-y-0 right-0 z-[9999] w-full md:w-[400px] bg-[#0a0a0c] border-l border-white/10 shadow-2xl transform transition-transform duration-300 ease-in-out flex flex-col ${
          isOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-white/10 bg-white/[0.02]">
          <div className="flex items-center gap-2 text-indigo-400">
            <Sparkles className="w-5 h-5" />
            <h2 className="font-mono font-bold tracking-wider text-sm">NEMOTRON COPILOT</h2>
          </div>
          <button 
            onClick={() => setIsOpen(false)}
            className="p-1.5 text-text-muted hover:text-white rounded-md hover:bg-white/5 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Context Chip */}
        {context && (
          <div className="px-4 py-2 bg-indigo-500/10 border-b border-indigo-500/20 text-xs font-mono text-indigo-200 flex flex-wrap items-center gap-1.5">
            <span className="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-bold uppercase tracking-wider text-[10px]">
              {context.page ? (context.page === "dashboard" ? "LIVE FORECAST" : context.page.toUpperCase()) : "OPERATIONAL"}
            </span>
            {context.lead_time_hours !== undefined && (
              <span className="px-1.5 py-0.5 rounded bg-white/5 text-amber-300 font-semibold text-[11px]">
                +{context.lead_time_hours}h
              </span>
            )}
            {context.variable && (
              <span className="px-1.5 py-0.5 rounded bg-white/5 text-cyan-300 text-[11px]">
                {context.variable.replace(/_/g, " ")}
              </span>
            )}
            {context.location && (
              <span className="px-1.5 py-0.5 rounded bg-white/5 text-text-secondary text-[11px]">
                {context.location}
              </span>
            )}
            {context.trace_id && (
              <span className="text-[10px] text-emerald-400 flex items-center gap-1 font-mono ml-auto">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Trace Linked
              </span>
            )}
          </div>
        )}

        {/* Message Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 font-sans text-sm">
          {messages.length === 0 && (
            <div className="text-center text-text-muted mt-8 space-y-4">
              <Bot className="w-12 h-12 mx-auto opacity-20" />
              <p>What would you like to investigate?</p>
              <div className="flex flex-wrap gap-2 justify-center mt-4">
                <button onClick={() => handleSend("Explain these weights")} className="px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-full text-xs transition-colors">
                  Explain these weights
                </button>
                <button onClick={() => handleSend("Why is the bust signal elevated?")} className="px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-full text-xs transition-colors">
                  Why is the bust signal elevated?
                </button>
                <button onClick={() => handleSend("Replay this forecast")} className="px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-full text-xs transition-colors">
                  Replay this forecast
                </button>
              </div>
            </div>
          )}
          
          {messages.map((msg: Message, i: number) => (
            <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[85%] rounded-lg p-3 ${
                msg.role === "user" 
                  ? "bg-indigo-600 text-white rounded-tr-sm" 
                  : "bg-white/10 text-text-primary rounded-tl-sm font-mono whitespace-pre-wrap text-xs"
              }`}>
                {msg.content}
                {msg.role === "assistant" && msg.content.includes("Source: Decision Trace") && (
                  <button 
                    onClick={() => setTraceOpen(true)}
                    className="mt-3 text-[10px] uppercase tracking-wider text-indigo-300 hover:text-indigo-200 flex items-center gap-1 border border-indigo-500/30 bg-indigo-500/10 px-2 py-1 rounded"
                  >
                    View Decision Trace
                  </button>
                )}
              </div>
            </div>
          ))}

          {currentTool && (
            <div className="flex items-center gap-2 text-xs font-mono text-indigo-400 opacity-70">
              <Loader2 className="w-3 h-3 animate-spin" />
              <span>executing {currentTool}...</span>
            </div>
          )}
          {isLoading && !currentTool && (
            <div className="flex items-center gap-2 text-xs font-mono text-text-muted">
              <Loader2 className="w-3 h-3 animate-spin" />
              <span>synthesizing evidence...</span>
            </div>
          )}
          <div ref={endOfMessagesRef} />
        </div>

        {/* Input Area */}
        <div className="p-4 border-t border-white/10 bg-white/[0.02]">
          <div className="flex gap-2">
            <input 
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend(input)}
              placeholder="Ask Forecast Forge..."
              className="flex-1 bg-black/50 border border-white/10 rounded-md px-3 py-2 text-sm text-white placeholder-white/30 focus:outline-none focus:border-indigo-500 font-mono"
            />
            <button 
              onClick={() => handleSend(input)}
              disabled={isLoading || !input.trim()}
              className="p-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:hover:bg-indigo-600 rounded-md text-white transition-colors"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {traceOpen && context && (
        <DecisionTraceDrawer
          isOpen={traceOpen}
          onClose={() => setTraceOpen(false)}
          lat={context.latitude}
          lon={context.longitude}
          validTime={context.valid_time}
          leadTime={context.lead_time_hours}
          variable={context.variable}
        />
      )}
    </>
  );
}
