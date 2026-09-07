import { useEffect } from 'react';
import { useFleetStore } from '../store/useFleetStore';

export function useSSE(url: string) {
  const addAlert = useFleetStore((state) => state.addAlert);

  useEffect(() => {
    const eventSource = new EventSource(url);
    
    eventSource.addEventListener('alert', (event) => {
      try {
        const data = JSON.parse(event.data);
        addAlert(data);
      } catch (e) {
        console.error("Failed to parse alert", e);
      }
    });

    return () => {
      eventSource.close();
    };
  }, [url, addAlert]);
}

