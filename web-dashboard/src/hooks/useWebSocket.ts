import { useEffect, useState, useCallback } from 'react'
import websocketClient, { type PriceUpdate, type StatsUpdate, type WebSocketMessage } from '../services/websocket'

interface UseWebSocketReturn {
  isConnected: boolean
  connectionState: string
  connect: () => Promise<void>
  disconnect: () => void
  send: (message: any) => boolean
  requestStats: () => boolean
  subscribe: (subscription: string) => boolean
}

export function useWebSocket(): UseWebSocketReturn {
  const [isConnected, setIsConnected] = useState(false)
  const [connectionState, setConnectionState] = useState('disconnected')

  const updateConnectionState = useCallback(() => {
    const state = websocketClient.getConnectionState()
    setConnectionState(state)
    setIsConnected(state === 'connected')
  }, [])

  const connect = useCallback(async () => {
    try {
      await websocketClient.connect()
      updateConnectionState()
    } catch (error) {
      console.error('Failed to connect to WebSocket:', error)
      updateConnectionState()
    }
  }, [updateConnectionState])

  const disconnect = useCallback(() => {
    websocketClient.disconnect()
    updateConnectionState()
  }, [updateConnectionState])

  const send = useCallback((message: any) => {
    return websocketClient.send(message)
  }, [])

  const requestStats = useCallback(() => {
    return websocketClient.requestStats()
  }, [])

  const subscribe = useCallback((subscription: string) => {
    return websocketClient.subscribe(subscription)
  }, [])

  useEffect(() => {
    // Подключаемся автоматически при монтировании
    connect()

    // Проверяем состояние соединения каждые 5 секунд
    const interval = setInterval(updateConnectionState, 5000)

    return () => {
      clearInterval(interval)
      // Не отключаемся автоматически, так как WebSocket должен работать глобально
    }
  }, [connect, updateConnectionState])

  return {
    isConnected,
    connectionState,
    connect,
    disconnect,
    send,
    requestStats,
    subscribe,
  }
}

export function usePriceUpdates(callback: (update: PriceUpdate) => void) {
  useEffect(() => {
    const unsubscribe = websocketClient.onPriceUpdate(callback)
    return unsubscribe
  }, [callback])
}

export function useStatsUpdates(callback: (stats: StatsUpdate) => void) {
  useEffect(() => {
    const unsubscribe = websocketClient.onStatsUpdate(callback)
    return unsubscribe
  }, [callback])
}

export function useWebSocketMessage(
  type: 'welcome' | 'price_update' | 'stats_update' | 'admin_message',
  callback: (message: WebSocketMessage) => void
) {
  useEffect(() => {
    const unsubscribe = websocketClient.onMessage(type, callback)
    return unsubscribe
  }, [type, callback])
} 