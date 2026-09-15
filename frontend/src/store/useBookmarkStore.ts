import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface BookmarkState {
  starredTrips: string[];
  toggleBookmark: (tripId: string) => void;
}

export const useBookmarkStore = create<BookmarkState>()(
  persist(
    (set) => ({
      starredTrips: [],
      toggleBookmark: (tripId) => set((state) => ({
        starredTrips: state.starredTrips.includes(tripId)
          ? state.starredTrips.filter((id) => id !== tripId)
          : [...state.starredTrips, tripId]
      })),
    }),
    {
      name: 'fleet-bookmarks', // saves to localStorage
    }
  )
);

