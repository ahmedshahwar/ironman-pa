import { useState, useEffect, useRef } from 'react';
import { Mic, X } from 'lucide-react';
import globeImage from '../globe.png';

const API_URL = import.meta.env.VITE_NGROK_URL || 'http://localhost:5000';
const DEEPGRAM_API_KEY = import.meta.env.VITE_DEEPGRAM_API || 'YOUR_DEEPGRAM_API_KEY';

interface VoiceInterfaceProps {
  onSwitchInterface: () => void;
  onInteraction: () => void;
  isVisible: boolean;
  controlsVisible: boolean;
}

const VoiceInterface = ({ onSwitchInterface, onInteraction, isVisible, controlsVisible }: VoiceInterfaceProps) => {
  const [responseText, setResponseText] = useState<string>('WELCOME, HOW MAY I ASSIST YOU');
  const [displayedText, setDisplayedText] = useState<string>('');
  const [audioUrl, setAudioUrl] = useState<string>('');
  const [isListening, setIsListening] = useState<boolean>(false);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [lastTranscript, setLastTranscript] = useState<string>('');
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [isDefaultText, setIsDefaultText] = useState<boolean>(true);
  const [isAnimatingText, setIsAnimatingText] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [isFirstOpen, setIsFirstOpen] = useState<boolean>(true);
  const [welcomeShown, setWelcomeShown] = useState<boolean>(false);
  
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const textAnimationRef = useRef<NodeJS.Timeout | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const initializedRef = useRef<boolean>(false);

  useEffect(() => {
    if (isVisible && !initializedRef.current) {
      initializedRef.current = true;
      const welcomeText = 'WELCOME, HOW MAY I ASSIST YOU';
      setResponseText(welcomeText);
      setIsDefaultText(true);
      // Only animate and speak the welcome text once
      animateText(welcomeText);
      generateSpeech(welcomeText);
      setWelcomeShown(true);
    } else if (!isVisible) {
      cleanupRecording();
      // Reset for next time the interface opens
      initializedRef.current = false;
    }
    
    return () => cleanupRecording();
  }, [isVisible]);

  const animateText = (text: string, audioDuration?: number) => {
    if (textAnimationRef.current) {
      clearInterval(textAnimationRef.current);
    }
    
    setDisplayedText('');
    setIsAnimatingText(true);
    
    let charIndex = 0;
    const maxDisplayLength = 150;
    const typingSpeed = audioDuration ? (audioDuration * 1000 / text.length) : 100;
    
    textAnimationRef.current = setInterval(() => {
      if (charIndex < text.length) {
        if (text.length <= maxDisplayLength) {
          setDisplayedText(text.substring(0, charIndex + 1));
        } else {
          const startIndex = Math.max(0, charIndex - maxDisplayLength + 1);
          setDisplayedText(text.substring(startIndex, charIndex + 1));
        }
        charIndex++;
      } else {
        if (textAnimationRef.current) {
          clearInterval(textAnimationRef.current);
        }
        if (text.length <= maxDisplayLength) {
          setDisplayedText(text);
        } else {
          setDisplayedText(text.substring(text.length - maxDisplayLength));
        }
        setIsAnimatingText(false);
      }
    }, typingSpeed);
  };

  const handleSwitchInterface = () => {
    cleanupRecording();
    onInteraction();
    onSwitchInterface();
  };

  const cleanupRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    
    if (textAnimationRef.current) {
      clearInterval(textAnimationRef.current);
    }
    
    setIsAnimatingText(false);
    setIsListening(false);
    mediaRecorderRef.current = null;
  };

  const startListening = async () => {
    if (isListening || isProcessing) return;
    
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      
      audioChunksRef.current = [];
      
      mediaRecorder.addEventListener('dataavailable', (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      });
      
      mediaRecorder.addEventListener('stop', async () => {
        setIsListening(false);
        setIsProcessing(true);
        
        try {
          const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
          const transcript = await transcribeAudio(audioBlob);
          
          if (transcript && transcript.trim()) {
            setLastTranscript(transcript);
            await sendToBackend(transcript);
          } else {
            setIsProcessing(false);
            setError("I couldn't hear what you said. Please try again.");
            animateText("I couldn't hear what you said. Please try again.");
          }
        } catch (error) {
          console.error('Error processing audio:', error);
          setIsProcessing(false);
          setError("Error processing your voice. Please try again.");
          animateText("Error processing your voice. Please try again.");
        }
      });
      
      setIsListening(true);
      mediaRecorder.start();
      
      setTimeout(() => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
          mediaRecorderRef.current.stop();
        }
      }, 8000);
      
    } catch (error) {
      console.error('Error accessing microphone:', error);
      setError("Couldn't access your microphone. Please check permissions.");
      animateText("Couldn't access your microphone. Please check permissions.");
    }
  };

  const transcribeAudio = async (audioBlob: Blob): Promise<string> => {
    try {
      const response = await fetch('https://api.deepgram.com/v1/listen?model=nova-2&language=en&detect_language=true&punctuate=true&smart_format=true', {
        method: 'POST',
        headers: {
          'Authorization': `Token ${DEEPGRAM_API_KEY}`,
          'Content-Type': audioBlob.type
        },
        body: audioBlob
      });
      
      if (!response.ok) {
        throw new Error(`Deepgram API error: ${response.status}`);
      }
      
      const data = await response.json();
      return data.results?.channels[0]?.alternatives[0]?.transcript || '';
    } catch (error) {
      console.error('Error transcribing with Deepgram:', error);
      throw error;
    }
  };

  const removeEmojis = (text: string): string => {
    // A simpler approach that targets common emoji unicode ranges
    return text.replace(/(\u00a9|\u00ae|[\u2000-\u3300]|\ud83c[\ud000-\udfff]|\ud83d[\ud000-\udfff]|\ud83e[\ud000-\udfff])/g, '').trim();
  };

  const generateSpeech = async (text: string) => {
    try {
      if (!text || typeof text !== 'string' || text.trim().length === 0) {
        throw new Error('Invalid text input for speech generation');
      }
  
      setIsProcessing(true);
      // Remove emojis for speech generation, but keep original text for display
      const cleanText = removeEmojis(text);
      if (!cleanText) {
        throw new Error('Text is empty after removing emojis');
      }

      const response = await fetch('https://api.deepgram.com/v1/speak?model=aura-asteria-en', {
        method: 'POST',
        headers: {
          'Authorization': `Token ${DEEPGRAM_API_KEY}`,
          'Content-Type': 'application/json',
          'Accept': 'audio/mp3'
        },
        body: JSON.stringify({
          text: cleanText
        })
      });
  
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Deepgram TTS API error: ${response.status} - ${errorText}`);
      }
  
      const audioBlob = await response.blob();
      const url = URL.createObjectURL(audioBlob);
      setAudioUrl(url);
      
      const audio = new Audio(url);
      audio.addEventListener('loadedmetadata', () => {
        setIsProcessing(false);
        // Only animate text if it's not the welcome message being repeated
        if (!(welcomeShown && text === 'WELCOME, HOW MAY I ASSIST YOU')) {
          animateText(text, audio.duration);
        }
      });
      await playAudio(url);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Error generating speech with Deepgram:', error);
      setError(`Speech generation failed: ${error.message}`);
      setResponseText(`Sorry, I couldn't generate speech: ${error.message}`);
      animateText(`Sorry, I couldn't generate speech: ${error.message}`);
      setIsProcessing(false);
    }
  };

  const sendToBackend = async (text: string) => {
    if (!text.trim()) return;
    
    try {
      const response = await fetch(`${API_URL}/api`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      });
      
      if (!response.ok) {
        throw new Error(`Server responded with ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('Backend response:', data);
      
      const newResponseText = data.response || "Looking into that for you right now. Give me a second!";
      setResponseText(newResponseText);
      setIsDefaultText(false);
      await generateSpeech(newResponseText);
    } catch (error) {
      console.error('Error sending transcript:', error);
      const errorText = `Sorry, there was an issue: ${error instanceof Error ? error.message : 'Unknown error'}`;
      setResponseText(errorText);
      setIsDefaultText(false);
      animateText(errorText);
    } finally {
      setIsProcessing(false);
    }
  };

  const playAudio = (url: string) => {
    return new Promise<void>((resolve) => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      
      const audio = new Audio(url);
      audioRef.current = audio;
      
      audio.onplay = () => setIsPlaying(true);
      audio.onended = () => {
        setIsPlaying(false);
        onInteraction();
        resolve();
      };
      audio.onerror = () => {
        console.error('Audio playback error');
        setIsPlaying(false);
        resolve();
      };
      
      audio.play()
        .then(() => console.log('Audio played successfully'))
        .catch((error) => {
          console.error('Error playing audio:', error);
          setIsPlaying(false);
          resolve();
        });
    });
  };

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    return (
      <div 
        className="absolute top-0 left-0 h-full w-full bg-white flex items-center justify-center z-20"
        style={{ 
          opacity: isVisible ? 1 : 0,
          pointerEvents: isVisible ? 'auto' : 'none',
          transition: 'opacity 0.3s ease'
        }}
      >
        <div className="text-center p-8 bg-white rounded-xl shadow-2xl">
          <p className="text-xl mb-4 text-gray-800">Your browser does not support voice recognition.</p>
          <button
            onClick={onSwitchInterface}
            className="px-6 py-3 rounded-full bg-gray-800 text-white font-medium hover:bg-gray-700 transition-colors"
          >
            Switch to Text Mode
          </button>
        </div>
      </div>
    );
  }

  return (
    <div 
      className="absolute top-0 left-0 h-full w-full bg-white z-20"
      style={{ 
        opacity: isVisible ? 1 : 0,
        pointerEvents: isVisible ? 'auto' : 'none',
        transition: 'all 0.3s ease'
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          // onInteraction();
        }
      }}
    >
      <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 flex flex-col items-center justify-center gap-8">
        <div 
          className="text-center w-96 h-32"
          style={{
            opacity: isVisible ? 1 : 0,
            transform: `translateY(${isVisible ? '0' : '10px'})`,
            transition: 'opacity 0.5s ease, transform 0.5s ease'
          }}
        >
          <p className="text-xl font-bold text-black break-words leading-tight">
            {displayedText}
            {isAnimatingText && (
              <span className="inline-block ml-1 animate-pulse">|</span>
            )}
          </p>
        </div>
        
        <div 
          className="relative w-64 h-64 rounded-full overflow-hidden transition-all duration-300 animate-wave"
          style={{
            transform: `scale(${isListening ? 1.1 : 1})`,
            transition: 'transform 0.3s ease-in-out'
          }}
        >
          <img 
            src={globeImage} 
            alt="Wavy Globe" 
            className="w-full h-full object-cover"
          />
          {/* Loading spinner removed from globe */}
        </div>
        
        {/* Separate loading indicator outside the globe */}
        {isProcessing && (
          <div className="mt-4">
            <div className="w-8 h-8 border-2 border-gray-400 border-t-transparent rounded-full animate-spin"></div>
          </div>
        )}
      </div>

      <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 flex items-center gap-4">
        <div className="flex gap-4 transition-all duration-300" style={{ 
          opacity: isVisible ? 1 : 0,
          transition: 'opacity 0.3s ease'
        }}>
          <button 
            className={`w-12 h-12 rounded-full bg-white flex items-center justify-center shadow-md ${isListening || isProcessing ? 'opacity-50' : ''}`}
            onClick={startListening}
            disabled={isListening || isProcessing}
          >
            <Mic size={20} className={isListening ? 'text-purple-600' : 'text-black'} />
          </button>
          <button 
            onClick={handleSwitchInterface}
            className="w-12 h-12 rounded-full bg-white flex items-center justify-center shadow-md"
          >
            <X size={20} className="text-black" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default VoiceInterface;