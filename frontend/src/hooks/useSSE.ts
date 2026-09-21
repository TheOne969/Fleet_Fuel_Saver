import { useEffect } from 'react';
import { useEffect, useRef } from 'react';
import { useFleetStore } from '../store/useFleetStore';

export function useSSE(url: string) {
  const addAlert = useFleetStore((state) => state.addAlert);
  const addAlerts = useFleetStore((state) => state.addAlerts);

  useEffect(() => {
    const eventSource = new EventSource(url);
    let buffer: any[] = [];
    
    eventSource.addEventListener('alert', (event) => {
      try {
        const data = JSON.parse(event.data);
        addAlert(data);
        buffer.push(data);
      } catch (e) {
        console.error("Failed to parse alert", e);
      }
    });

    const interval = setInterval(() => {
      if (buffer.length > 0) {
        // Only trigger a React re-render once every 500ms with the batched alerts
        addAlerts(buffer);
        buffer = [];
      }
    }, 500);

    return () => {
      eventSource.close();
      clearInterval(interval);
    };
  }, [url, addAlert]);
  }, [url, addAlerts]);
}

