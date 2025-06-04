import { useState, useCallback } from 'react'
import { Box, Grid, Paper, Typography, Card, CardContent, Chip, IconButton, Switch, FormControlLabel } from '@mui/material'
import {
  TrendingUp as TrendingUpIcon,
  Store as StoreIcon,
  Business as BusinessIcon,
  AttachMoney as MoneyIcon,
  Speed as SpeedIcon,
  CheckCircle as CheckCircleIcon,
  Refresh as RefreshIcon,
  Wifi as WifiIcon,
  WifiOff as WifiOffIcon,
} from '@mui/icons-material'

import StatCard from '../../components/StatCard/StatCard'
import PriceChart from '../../components/Charts/PriceChart'
import SavingsChart from '../../components/Charts/SavingsChart'
import TopDeals from '../../components/TopDeals/TopDeals'
import RecentActivity from '../../components/RecentActivity/RecentActivity'
import { useWebSocket, useStatsUpdates, usePriceUpdates } from '../../hooks/useWebSocket'
import type { StatsUpdate, PriceUpdate } from '../../services/websocket'

export default function Dashboard() {
  const [chartType, setChartType] = useState<'line' | 'area'>('area')
  const [savingsChartType, setSavingsChartType] = useState<'bar' | 'pie'>('bar')
  const [realTimeStats, setRealTimeStats] = useState<StatsUpdate | null>(null)
  const [recentPriceUpdates, setRecentPriceUpdates] = useState<PriceUpdate[]>([])
  const [enableNotifications, setEnableNotifications] = useState(true)

  const { isConnected, connectionState, requestStats } = useWebSocket()

  // Обработчик real-time обновлений статистики
  const handleStatsUpdate = useCallback((stats: StatsUpdate) => {
    console.log('📊 Received stats update:', stats)
    setRealTimeStats(stats)
  }, [])

  // Обработчик real-time обновлений цен
  const handlePriceUpdate = useCallback((update: PriceUpdate) => {
    console.log('💰 Received price update:', update)
    
    // Добавляем в список последних обновлений (максимум 10)
    setRecentPriceUpdates(prev => [update, ...prev.slice(0, 9)])
  }, [])

  // Подписываемся на real-time события
  useStatsUpdates(handleStatsUpdate)
  usePriceUpdates(handlePriceUpdate)

  // Используем real-time статистику если доступна, иначе mock данные
  const stats = realTimeStats || {
    total_products: 1247,
    total_suppliers: 23,
    total_prices: 5420,
    avg_savings: 15.3,
    updates_today: 342,
    api_response_time: 120,
    system_health: 'excellent',
    last_update: new Date().toISOString(),
  }

  const getSystemHealthColor = (health: string) => {
    switch (health) {
      case 'excellent': return 'success'
      case 'good': return 'info'
      case 'warning': return 'warning'
      case 'critical': return 'error'
      default: return 'info'
    }
  }

  const getConnectionIcon = () => {
    return isConnected ? (
      <WifiIcon sx={{ color: 'success.main' }} />
    ) : (
      <WifiOffIcon sx={{ color: 'error.main' }} />
    )
  }

  return (
    <Box>
      {/* Заголовок с real-time статусом */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            🏝️ Dashboard - Monito Unified v3.0
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Real-time система управления ценами поставщиков острова Бали
          </Typography>
        </Box>
        
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Chip
            icon={getConnectionIcon()}
            label={`WebSocket: ${connectionState}`}
            color={isConnected ? 'success' : 'error'}
            variant={isConnected ? 'filled' : 'outlined'}
          />
          
          <IconButton 
            onClick={requestStats}
            disabled={!isConnected}
            sx={{ 
              backgroundColor: 'primary.main',
              color: 'white',
              '&:hover': {
                backgroundColor: 'primary.dark'
              }
            }}
          >
            <RefreshIcon />
          </IconButton>
        </Box>
      </Box>

      {/* Статистические карточки */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={4}>
          <StatCard
            title="Товаров в каталоге"
            value={stats.total_products.toLocaleString()}
            icon={<StoreIcon fontSize="large" />}
            color="primary"
            subtitle="Unified каталог"
            trend={realTimeStats ? "🔄 Live" : "+12% за месяц"}
          />
        </Grid>
        
        <Grid item xs={12} sm={6} md={4}>
          <StatCard
            title="Активных поставщиков"
            value={stats.total_suppliers.toString()}
            icon={<BusinessIcon fontSize="large" />}
            color="secondary"
            subtitle="Проверенные поставщики"
            trend="+2 новых"
          />
        </Grid>
        
        <Grid item xs={12} sm={6} md={4}>
          <StatCard
            title="Средняя экономия"
            value={`${stats.avg_savings}%`}
            icon={<MoneyIcon fontSize="large" />}
            color="success"
            subtitle="По unified каталогу"
            trend={realTimeStats?.price_trends ? 
              `${realTimeStats.price_trends.trend_direction === 'up' ? '📈' : '📉'} ${realTimeStats.price_trends.trend_percent}%` : 
              "+2.1% vs прошлый месяц"
            }
          />
        </Grid>
        
        <Grid item xs={12} sm={6} md={4}>
          <StatCard
            title="Обновлений сегодня"
            value={stats.updates_today.toString()}
            icon={<TrendingUpIcon fontSize="large" />}
            color="info"
            subtitle="Цены и товары"
            trend={realTimeStats ? "🔄 Real-time" : "Последнее: 2 мин назад"}
          />
        </Grid>
        
        <Grid item xs={12} sm={6} md={4}>
          <StatCard
            title="API Response Time"
            value={`${stats.api_response_time}ms`}
            icon={<SpeedIcon fontSize="large" />}
            color="warning"
            subtitle="Средний ответ"
            trend="Excellent"
          />
        </Grid>
        
        <Grid item xs={12} sm={6} md={4}>
          <StatCard
            title="System Health"
            value="100%"
            icon={<CheckCircleIcon fontSize="large" />}
            color={getSystemHealthColor(stats.system_health) as any}
            subtitle="Все системы работают"
            trend="Uptime: 99.9%"
          />
        </Grid>
      </Grid>

      {/* Графики и аналитика */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} lg={8}>
          <Paper sx={{ p: 3, height: 450 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">
                📈 Тренды цен (последние 30 дней)
              </Typography>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Chip 
                  label="Area"
                  color={chartType === 'area' ? 'primary' : 'default'}
                  onClick={() => setChartType('area')}
                  size="small"
                />
                <Chip 
                  label="Line"
                  color={chartType === 'line' ? 'primary' : 'default'}
                  onClick={() => setChartType('line')}
                  size="small"
                />
              </Box>
            </Box>
            <PriceChart type={chartType} height={350} />
          </Paper>
        </Grid>
        
        <Grid item xs={12} lg={4}>
          <Paper sx={{ p: 3, height: 450 }}>
            <Typography variant="h6" gutterBottom>
              🔥 Топовые предложения
            </Typography>
            <TopDeals />
          </Paper>
        </Grid>
      </Grid>

      {/* Дополнительная аналитика */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} lg={6}>
          <Paper sx={{ p: 3, height: 400 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">
                💰 Экономия по категориям
              </Typography>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Chip 
                  label="Bar"
                  color={savingsChartType === 'bar' ? 'primary' : 'default'}
                  onClick={() => setSavingsChartType('bar')}
                  size="small"
                />
                <Chip 
                  label="Pie"
                  color={savingsChartType === 'pie' ? 'primary' : 'default'}
                  onClick={() => setSavingsChartType('pie')}
                  size="small"
                />
              </Box>
            </Box>
            <SavingsChart type={savingsChartType} height={320} />
          </Paper>
        </Grid>
        
        <Grid item xs={12} lg={6}>
          <Paper sx={{ p: 3, height: 400 }}>
            <Typography variant="h6" gutterBottom>
              🕒 Последняя активность
            </Typography>
            <RecentActivity />
          </Paper>
        </Grid>
      </Grid>

      {/* Real-time Price Updates */}
      {recentPriceUpdates.length > 0 && (
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={12}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                ⚡ Последние изменения цен (real-time)
              </Typography>
              <Grid container spacing={2}>
                {recentPriceUpdates.slice(0, 6).map((update, index) => (
                  <Grid item xs={12} sm={6} md={4} key={index}>
                    <Card sx={{ 
                      border: 1, 
                      borderColor: update.price_change_percent > 0 ? 'warning.main' : 'success.main',
                      borderRadius: 2
                    }}>
                      <CardContent sx={{ pb: 2 }}>
                        <Typography variant="subtitle2" gutterBottom>
                          {update.product_name}
                        </Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                          {update.supplier} • {update.category}
                        </Typography>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <Typography variant="body2">
                            {new Intl.NumberFormat('id-ID', {
                              style: 'currency',
                              currency: 'IDR',
                              minimumFractionDigits: 0,
                            }).format(update.new_price)}
                          </Typography>
                          <Chip
                            label={`${update.price_change_percent > 0 ? '+' : ''}${update.price_change_percent.toFixed(1)}%`}
                            color={update.price_change_percent > 0 ? 'warning' : 'success'}
                            size="small"
                          />
                        </Box>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            </Paper>
          </Grid>
        </Grid>
      )}

      {/* Настройки */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              🚀 Быстрые действия
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Card sx={{ cursor: 'pointer', '&:hover': { bgcolor: 'action.hover' } }}>
                <CardContent>
                  <Typography variant="subtitle1">🔍 Поиск в unified каталоге</Typography>
                  <Typography variant="body2" color="text.secondary">
                    Найти товары с лучшими ценами от всех поставщиков
                  </Typography>
                </CardContent>
              </Card>
              
              <Card sx={{ cursor: 'pointer', '&:hover': { bgcolor: 'action.hover' } }}>
                <CardContent>
                  <Typography variant="subtitle1">📤 Загрузить прайс-лист</Typography>
                  <Typography variant="body2" color="text.secondary">
                    Добавить новый прайс-лист поставщика в систему
                  </Typography>
                </CardContent>
              </Card>
              
              <Card sx={{ cursor: 'pointer', '&:hover': { bgcolor: 'action.hover' } }}>
                <CardContent>
                  <Typography variant="subtitle1">📊 Создать отчет</Typography>
                  <Typography variant="body2" color="text.secondary">
                    Сгенерировать отчет по ценам и экономии
                  </Typography>
                </CardContent>
              </Card>
            </Box>
          </Paper>
        </Grid>
        
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              ⚙️ Real-time настройки
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={enableNotifications}
                    onChange={(e) => setEnableNotifications(e.target.checked)}
                  />
                }
                label="Уведомления об изменениях цен"
              />
              
              <Typography variant="body2" color="text.secondary">
                WebSocket статус: {connectionState}
              </Typography>
              
              {realTimeStats && (
                <Typography variant="body2" color="success.main">
                  ✅ Получено {recentPriceUpdates.length} обновлений цен
                </Typography>
              )}
            </Box>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  )
} 