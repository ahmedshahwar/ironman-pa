import React, { useState, useRef, useEffect } from 'react';
import { Send } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import type { Message } from '../types';

const API_URL = import.meta.env.VITE_NGROK_URL || 'http://localhost:5000';

interface TextInterfaceProps {
  onSwitchInterface: () => void;
  isVisible: boolean;
  onControlsVisibleChange: (visible: boolean) => void;
  controlsVisible: boolean;
}

export default function TextInterface({ 
  onSwitchInterface, 
  isVisible, 
  onControlsVisibleChange,
  controlsVisible 
}: TextInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
  
    const newMessage: Message = { role: 'user', content: input };
    setMessages(prev => [...prev, newMessage]);
    setInput('');
    setIsLoading(true);
  
    try {
      console.log('Fetching:', `${API_URL}/api`); // Debug log
      const response = await fetch(`${API_URL}/api`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: input }),
      });
  
      const data = await response.json();
      setMessages(prev => [...prev, { role: 'assistant', content: data.response }]);
    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: 'Sorry, I encountered an error processing your request.' 
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSubmit(e);
    }
  };

  const handleToggleClick = () => {
    onControlsVisibleChange(true);
    onSwitchInterface();
  };

  // Rest of your JSX remains unchanged
  return (
    <div className="h-screen w-screen bg-white p-6">
      <div className="flex justify-between items-center p-4 mb-4">
        <h1 className="text-2xl font-bold text-gray-800 tracking-wide">
          Personal Assistant
        </h1>
      </div>

      <div className="flex-1 overflow-y-auto px-4 space-y-4 h-[calc(100vh-200px)]">
        {messages.map((message, index) => (
          <div key={index} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] p-4 rounded-2xl ${message.role === 'user' ? 'bg-[#C8D0F8] text-gray-800' : 'bg-[#C8D0F8] text-gray-800'}`}>
              <ReactMarkdown className="text-lg font-medium prose max-w-none">{message.content}</ReactMarkdown>
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-[#C8D0F8] p-4 rounded-2xl">
              <div className="flex gap-2">
                <div className="w-2 h-2 bg-gray-600 rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-gray-600 rounded-full animate-bounce [animation-delay:-.3s]" />
                <div className="w-2 h-2 bg-gray-600 rounded-full animate-bounce [animation-delay:-.5s]" />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="relative">
        <div className="absolute bottom-20 right-4 flex items-center gap-4">
          <button
            onClick={handleToggleClick}
            className="p-4 rounded-full shadow-lg transition-transform hover:scale-105 active:scale-95"
            style={{
              background: 'white',
              width: '80px',
              height: '80px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: '0px solid transparent',
              borderRadius: '50%',
              backgroundImage: 'linear-gradient(white, white), linear-gradient(135deg, #A0B8F8, #D8C8F8)',
              backgroundOrigin: 'border-box',
              backgroundClip: 'content-box, border-box',
            }}
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="24"
              height="24"
              viewBox="0 0 28 28"
              fill="currentColor"
              stroke="currentColor"
              strokeWidth="1"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="text-gray-800"
            >
              <rect x="0" y="11" width="3" height="8" rx="0.8" />
              <rect x="5" y="7" width="3" height="16" rx="0.8" />
              <rect x="10" y="4" width="3" height="22" rx="0.8" />
              <rect x="15" y="10" width="3" height="10" rx="0.8" />
              <rect x="20" y="7" width="3" height="16" rx="0.8" />
              <rect x="25" y="11" width="3" height="8" rx="0.8" />
            </svg>
          </button>
        </div>

        <div className="p-4 bg-transparent">
          <div className="flex gap-4">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your message..."
              className="flex-1 bg-white text-gray-800 rounded-full px-6 py-3 focus:outline-none focus:ring-2 focus:ring-[#C8D0F8] placeholder-gray-600 border border-gray-300"
            />
            <button
              type="submit"
              onClick={handleSubmit}
              disabled={isLoading}
              className="p-3 rounded-full bg-gradient-to-r from-[#C8D0F8] to-[#A0B8F8] text-gray-800 hover:opacity-80 transition-opacity disabled:opacity-50"
            >
              <Send size={22} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}