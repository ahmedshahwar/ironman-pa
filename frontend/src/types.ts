export interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export interface VoiceState {
  isListening: boolean;
  isSpeaking: boolean;
}