import toast from 'react-hot-toast'

type MessageType = 'welcome' | 'price_update' | 'stats_update' | 'admin_message'

interface WebSocketMessage {
  type: MessageType
  data?: any
  message?: string
  timestamp: string
}

interface PriceUpdate {
  product_name: string
  supplier: string
  old_price: number
  new_price: number
  price_change_percent: number
  category: string
  updated_at: string
}

interface StatsUpdate {
  total_products: number
  total_suppliers: number
  total_prices: number
  avg_savings: number
  updates_today: number
  api_response_time: number
  system_health: string
  last_update: string
  price_trends?: {
    trend_direction: string
    trend_percent: number
  }
  top_categories?: Array<{
    name: string
    savings: number
  }>
}

type MessageHandler = (message: WebSocketMessage) => void
type PriceUpdateHandler = (update: PriceUpdate) => void
type StatsUpdateHandler = (stats: StatsUpdate) => void

class WebSocketClient {
  private ws: WebSocket | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private isConnecting = false
  private messageHandlers: Map<MessageType, MessageHandler[]> = new Map()
  private priceUpdateHandlers: PriceUpdateHandler[] = []
  private statsUpdateHandlers: StatsUpdateHandler[] = []
  
  constructor(private url: string = 'ws://localhost:8000/ws/connect') {
    this.initializeHandlers()
  }

  private initializeHandlers() {
    // Инициализируем map для обработчиков
    this.messageHandlers.set('welcome', [])
    this.messageHandlers.set('price_update', [])
    this.messageHandlers.set('stats_update', [])
    this.messageHandlers.set('admin_message', [])
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        resolve()
        return
      }

      if (this.isConnecting) {
        reject(new Error('Connection already in progress'))
        return
      }

      this.isConnecting = true

      try {
        this.ws = new WebSocket(this.url)

        this.ws.onopen = () => {
          console.log('🚀 WebSocket connected')
          this.isConnecting = false
          this.reconnectAttempts = 0
          this.reconnectDelay = 1000
          
          toast.success('🔄 Real-time подключение установлено', {
            duration: 3000,
            position: 'top-right'
          })
          
          resolve()
        }

        this.ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data)
            this.handleMessage(message)
          } catch (error) {
            console.error('Error parsing WebSocket message:', error)
          }
        }

        this.ws.onclose = (event) => {
          console.log('WebSocket closed:', event.code, event.reason)
          this.isConnecting = false
          this.ws = null
          
          if (!event.wasClean && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect()
          } else {
            toast.error('Real-time подключение потеряно', {
              duration: 5000
            })
          }
        }

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error)
          this.isConnecting = false
          
          if (this.reconnectAttempts === 0) {
            reject(error)
          }
        }

      } catch (error) {
        this.isConnecting = false
        reject(error)
      }
    })
  }

  private scheduleReconnect() {
    this.reconnectAttempts++
    
    console.log(`Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`)
    
    setTimeout(() => {
      this.connect().catch(() => {
        this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000)
      })
    }, this.reconnectDelay)
  }

  private handleMessage(message: WebSocketMessage) {
    console.log('Received WebSocket message:', message)

    // Вызываем общие обработчики
    const handlers = this.messageHandlers.get(message.type) || []
    handlers.forEach(handler => handler(message))

    // Специальная обработка для разных типов сообщений
    switch (message.type) {
      case 'welcome':
        console.log('Welcome message:', message.message)
        break

      case 'price_update':
        if (message.data) {
          this.priceUpdateHandlers.forEach(handler => handler(message.data))
          this.showPriceUpdateNotification(message.data)
        }
        break

      case 'stats_update':
        if (message.data) {
          this.statsUpdateHandlers.forEach(handler => handler(message.data))
        }
        break

      case 'admin_message':
        toast(message.data?.message || 'Admin notification', {
          duration: 6000,
          icon: '📢'
        })
        break
    }
  }

  private showPriceUpdateNotification(update: PriceUpdate) {
    const priceChange = update.price_change_percent
    const isIncrease = priceChange > 0
    const changeText = isIncrease ? 'увеличилась' : 'снизилась'
    const icon = isIncrease ? '📈' : '📉'
    
    const formatPrice = (price: number) => {
      return new Intl.NumberFormat('id-ID', {
        style: 'currency',
        currency: 'IDR',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
      }).format(price)
    }

    toast(
      `${icon} ${update.product_name}\n` +
      `Цена ${changeText} на ${Math.abs(priceChange).toFixed(1)}%\n` +
      `${formatPrice(update.old_price)} → ${formatPrice(update.new_price)}`,
      {
        duration: 5000,
        style: {
          background: isIncrease ? '#fff3e0' : '#e8f5e8',
          color: isIncrease ? '#ef6c00' : '#2e7d32'
        }
      }
    )
  }

  // Методы подписки на события
  onPriceUpdate(handler: PriceUpdateHandler): () => void {
    this.priceUpdateHandlers.push(handler)
    return () => {
      const index = this.priceUpdateHandlers.indexOf(handler)
      if (index > -1) {
        this.priceUpdateHandlers.splice(index, 1)
      }
    }
  }

  onStatsUpdate(handler: StatsUpdateHandler): () => void {
    this.statsUpdateHandlers.push(handler)
    return () => {
      const index = this.statsUpdateHandlers.indexOf(handler)
      if (index > -1) {
        this.statsUpdateHandlers.splice(index, 1)
      }
    }
  }

  onMessage(type: MessageType, handler: MessageHandler): () => void {
    const handlers = this.messageHandlers.get(type) || []
    handlers.push(handler)
    this.messageHandlers.set(type, handlers)

    return () => {
      const currentHandlers = this.messageHandlers.get(type) || []
      const index = currentHandlers.indexOf(handler)
      if (index > -1) {
        currentHandlers.splice(index, 1)
        this.messageHandlers.set(type, currentHandlers)
      }
    }
  }

  // Отправка сообщений серверу
  send(message: any): boolean {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
      return true
    }
    console.warn('WebSocket is not connected')
    return false
  }

  requestStats(): boolean {
    return this.send({ type: 'request_stats' })
  }

  subscribe(subscription: string): boolean {
    return this.send({ type: 'subscribe', subscription })
  }

  disconnect() {
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect')
      this.ws = null
    }
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  getConnectionState(): string {
    if (!this.ws) return 'disconnected'
    
    switch (this.ws.readyState) {
      case WebSocket.CONNECTING: return 'connecting'
      case WebSocket.OPEN: return 'connected'
      case WebSocket.CLOSING: return 'closing'
      case WebSocket.CLOSED: return 'disconnected'
      default: return 'unknown'
    }
  }
}

// Создаем singleton экземпляр
const websocketClient = new WebSocketClient()

export default websocketClient
export type { PriceUpdate, StatsUpdate, WebSocketMessage } 