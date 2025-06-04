import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'

// Типы для состояния
interface User {
  id: number
  name: string
  email: string
  role: string
}

interface AppSettings {
  theme: 'light' | 'dark'
  language: 'en' | 'id' | 'ru'
  itemsPerPage: number
  enableNotifications: boolean
  enableAnalytics: boolean
}

interface SystemStats {
  totalProducts: number
  totalSuppliers: number
  totalPrices: number
  avgSavings: number
  lastUpdate: string
  systemHealth: 'excellent' | 'good' | 'warning' | 'critical'
}

interface AppState {
  // User state
  user: User | null
  isAuthenticated: boolean
  
  // App settings
  settings: AppSettings
  
  // System state
  isLoading: boolean
  error: string | null
  systemStats: SystemStats | null
  
  // Search state
  searchQuery: string
  searchFilters: {
    category: string
    supplier: string
    priceMin: number
    priceMax: number
    sortBy: string
  }
  
  // Actions
  setUser: (user: User | null) => void
  setAuthenticated: (isAuthenticated: boolean) => void
  updateSettings: (settings: Partial<AppSettings>) => void
  setLoading: (isLoading: boolean) => void
  setError: (error: string | null) => void
  setSystemStats: (stats: SystemStats) => void
  setSearchQuery: (query: string) => void
  updateSearchFilters: (filters: Partial<AppState['searchFilters']>) => void
  resetSearchFilters: () => void
}

const defaultSettings: AppSettings = {
  theme: 'light',
  language: 'ru',
  itemsPerPage: 20,
  enableNotifications: true,
  enableAnalytics: true,
}

const defaultSearchFilters = {
  category: '',
  supplier: '',
  priceMin: 0,
  priceMax: 1000000,
  sortBy: 'best_price',
}

export const useStore = create<AppState>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial state
        user: null,
        isAuthenticated: false,
        settings: defaultSettings,
        isLoading: false,
        error: null,
        systemStats: null,
        searchQuery: '',
        searchFilters: defaultSearchFilters,

        // Actions
        setUser: (user) => set({ user }),
        
        setAuthenticated: (isAuthenticated) => set({ isAuthenticated }),
        
        updateSettings: (newSettings) =>
          set((state) => ({
            settings: { ...state.settings, ...newSettings },
          })),
        
        setLoading: (isLoading) => set({ isLoading }),
        
        setError: (error) => set({ error }),
        
        setSystemStats: (systemStats) => set({ systemStats }),
        
        setSearchQuery: (searchQuery) => set({ searchQuery }),
        
        updateSearchFilters: (newFilters) =>
          set((state) => ({
            searchFilters: { ...state.searchFilters, ...newFilters },
          })),
        
        resetSearchFilters: () =>
          set({ 
            searchQuery: '',
            searchFilters: defaultSearchFilters 
          }),
      }),
      {
        name: 'monito-dashboard-storage',
        partialize: (state) => ({
          user: state.user,
          isAuthenticated: state.isAuthenticated,
          settings: state.settings,
          searchFilters: state.searchFilters,
        }),
      }
    ),
    {
      name: 'monito-dashboard',
    }
  )
)

// Селекторы для удобного доступа к состоянию
export const useUser = () => useStore((state) => state.user)
export const useIsAuthenticated = () => useStore((state) => state.isAuthenticated)
export const useSettings = () => useStore((state) => state.settings)
export const useIsLoading = () => useStore((state) => state.isLoading)
export const useError = () => useStore((state) => state.error)
export const useSystemStats = () => useStore((state) => state.systemStats)
export const useSearchQuery = () => useStore((state) => state.searchQuery)
export const useSearchFilters = () => useStore((state) => state.searchFilters)

// Actions селекторы
export const useAppActions = () => {
  const {
    setUser,
    setAuthenticated,
    updateSettings,
    setLoading,
    setError,
    setSystemStats,
    setSearchQuery,
    updateSearchFilters,
    resetSearchFilters,
  } = useStore()

  return {
    setUser,
    setAuthenticated,
    updateSettings,
    setLoading,
    setError,
    setSystemStats,
    setSearchQuery,
    updateSearchFilters,
    resetSearchFilters,
  }
} 