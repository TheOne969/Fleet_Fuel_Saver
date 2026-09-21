import { create } from 'zustand';

interface Alert {
  trip_id: string;
  type: string;
  severity: string;
  reason: string;
  timestamp: string | number;
}

interface FleetStore {
  alerts: Alert[];
  addAlert: (alert: Alert) => void;
  addAlerts: (newAlerts: Alert[]) => void;
}

export const useFleetStore = create<FleetStore>((set) => ({
  alerts: [],
  addAlert: (alert) => set((state) => ({ 
      alerts: [alert, ...state.alerts].slice(0, 100) 
  })),
  addAlerts: (newAlerts) => set((state) => ({
      alerts: [...newAlerts.reverse(), ...state.alerts].slice(0, 100)
  })),
}));
