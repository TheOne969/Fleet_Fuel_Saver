import { create } from 'zustand';

interface Alert {
  trip_id: string;
  type: string;
  rpm: number;
  speed: number;
  z_score: number;
  timestamp: number;
}

interface FleetStore {
  alerts: Alert[];
  addAlert: (alert: Alert) => void;
}

export const useFleetStore = create<FleetStore>((set) => ({
  alerts: [],
  addAlert: (alert) => set((state) => ({ 
      alerts: [alert, ...state.alerts].slice(0, 100) 
  })),
}));

