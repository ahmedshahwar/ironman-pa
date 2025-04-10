import React, { useState, useEffect, useRef } from 'react';
import TextInterface from './TextInterface';
import VoiceInterface from './VoiceInterface';

const App: React.FC = () => {
  const [activeInterface, setActiveInterface] = useState<'text' | 'voice'>('text');
  const [voiceVisible, setVoiceVisible] = useState<boolean>(false);
  const [controlsVisible, setControlsVisible] = useState<boolean>(false);
  const inactivityTimerRef = useRef<NodeJS.Timeout | null>(null);

  const handleSwitchInterface = () => {
    if (activeInterface === 'text') {
      setControlsVisible(true);
      setTimeout(() => {
        setVoiceVisible(true);
        setActiveInterface('voice');
        resetInactivityTimer();
      }, 300);
    } else {
      setVoiceVisible(false);
      setActiveInterface('text');
      setControlsVisible(false);
    }
  };

  const resetInactivityTimer = () => {
    if (inactivityTimerRef.current) {
      clearTimeout(inactivityTimerRef.current);
    }
    
    // Only set an inactivity timer for showing controls, not for closing the interface
    if (activeInterface === 'voice') {
      inactivityTimerRef.current = setTimeout(() => {
        setControlsVisible(false);
      }, 5000);
    }
  };

  const handleVoiceInteraction = () => {
    if (activeInterface === 'voice') {
      setControlsVisible(true);
      resetInactivityTimer();
    }
  };

  useEffect(() => {
    return () => {
      if (inactivityTimerRef.current) {
        clearTimeout(inactivityTimerRef.current);
      }
    };
  }, []);

  return (
    <div className="relative h-screen w-screen overflow-hidden">
      <TextInterface 
        onSwitchInterface={handleSwitchInterface}
        onControlsVisibleChange={setControlsVisible}
        isVisible={true}
        controlsVisible={controlsVisible}
      />
      <VoiceInterface 
        onSwitchInterface={handleSwitchInterface}
        onInteraction={handleVoiceInteraction}
        isVisible={voiceVisible}
        controlsVisible={controlsVisible}
      />
    </div>
  );
};

export default App;