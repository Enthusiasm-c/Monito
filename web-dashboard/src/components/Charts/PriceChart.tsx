import { Box, Typography, CircularProgress } from '@mui/material'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area,
} from 'recharts'
import { format } from 'date-fns'
import { ru } from 'date-fns/locale'

interface PriceDataPoint {
  date: string
  avgPrice: number
  bestPrice: number
  worstPrice: number
  savings: number
  timestamp: number
}

interface PriceChartProps {
  data?: PriceDataPoint[]
  loading?: boolean
  title?: string
  type?: 'line' | 'area'
  height?: number
}

// Mock данные для демонстрации
const mockPriceData: PriceDataPoint[] = [
  {
    date: '01.01',
    avgPrice: 15500,
    bestPrice: 13500,
    worstPrice: 18000,
    savings: 12.9,
    timestamp: Date.now() - 29 * 24 * 60 * 60 * 1000,
  },
  {
    date: '05.01',
    avgPrice: 15200,
    bestPrice: 13200,
    worstPrice: 17800,
    savings: 13.4,
    timestamp: Date.now() - 25 * 24 * 60 * 60 * 1000,
  },
  {
    date: '10.01',
    avgPrice: 14800,
    bestPrice: 12800,
    worstPrice: 17200,
    savings: 14.8,
    timestamp: Date.now() - 20 * 24 * 60 * 60 * 1000,
  },
  {
    date: '15.01',
    avgPrice: 14500,
    bestPrice: 12500,
    worstPrice: 16800,
    savings: 15.3,
    timestamp: Date.now() - 15 * 24 * 60 * 60 * 1000,
  },
  {
    date: '20.01',
    avgPrice: 14200,
    bestPrice: 12200,
    worstPrice: 16500,
    savings: 16.1,
    timestamp: Date.now() - 10 * 24 * 60 * 60 * 1000,
  },
  {
    date: '25.01',
    avgPrice: 13900,
    bestPrice: 11900,
    worstPrice: 16200,
    savings: 16.8,
    timestamp: Date.now() - 5 * 24 * 60 * 60 * 1000,
  },
  {
    date: 'Сегодня',
    avgPrice: 13600,
    bestPrice: 11600,
    worstPrice: 15800,
    savings: 17.5,
    timestamp: Date.now(),
  },
]

const formatPrice = (value: number) => {
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value)
}

const formatTooltipDate = (timestamp: number) => {
  return format(new Date(timestamp), 'dd MMMM yyyy', { locale: ru })
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload
    return (
      <Box
        sx={{
          backgroundColor: 'background.paper',
          border: 1,
          borderColor: 'divider',
          borderRadius: 1,
          p: 2,
          boxShadow: 2,
        }}
      >
        <Typography variant="subtitle2" gutterBottom>
          {formatTooltipDate(data.timestamp)}
        </Typography>
        {payload.map((entry: any, index: number) => (
          <Typography
            key={index}
            variant="body2"
            sx={{ color: entry.color, display: 'flex', alignItems: 'center', gap: 1 }}
          >
            <Box
              sx={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                backgroundColor: entry.color,
              }}
            />
            {entry.name}: {formatPrice(entry.value)}
            {entry.dataKey === 'savings' && '%'}
          </Typography>
        ))}
        <Typography variant="caption" color="success.main" sx={{ mt: 1, display: 'block' }}>
          💰 Экономия: {data.savings}%
        </Typography>
      </Box>
    )
  }
  return null
}

export default function PriceChart({
  data = mockPriceData,
  loading = false,
  title = '📈 Тренды цен за последние 30 дней',
  type = 'area',
  height = 300,
}: PriceChartProps) {
  if (loading) {
    return (
      <Box
        sx={{
          height,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexDirection: 'column',
          gap: 2,
        }}
      >
        <CircularProgress />
        <Typography variant="body2" color="text.secondary">
          Загрузка данных...
        </Typography>
      </Box>
    )
  }

  const Chart = type === 'area' ? AreaChart : LineChart

  return (
    <Box sx={{ width: '100%', height }}>
      <ResponsiveContainer width="100%" height="100%">
        <Chart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <defs>
            <linearGradient id="colorBestPrice" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#4caf50" stopOpacity={0.8} />
              <stop offset="95%" stopColor="#4caf50" stopOpacity={0.1} />
            </linearGradient>
            <linearGradient id="colorAvgPrice" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#2196f3" stopOpacity={0.8} />
              <stop offset="95%" stopColor="#2196f3" stopOpacity={0.1} />
            </linearGradient>
            <linearGradient id="colorWorstPrice" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#f44336" stopOpacity={0.8} />
              <stop offset="95%" stopColor="#f44336" stopOpacity={0.1} />
            </linearGradient>
          </defs>
          
          <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
          <XAxis 
            dataKey="date" 
            stroke="#666"
            fontSize={12}
          />
          <YAxis 
            stroke="#666"
            fontSize={12}
            tickFormatter={formatPrice}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend />

          {type === 'area' ? (
            <>
              <Area
                type="monotone"
                dataKey="bestPrice"
                stroke="#4caf50"
                fillOpacity={1}
                fill="url(#colorBestPrice)"
                strokeWidth={2}
                name="Лучшая цена"
              />
              <Area
                type="monotone"
                dataKey="avgPrice"
                stroke="#2196f3"
                fillOpacity={1}
                fill="url(#colorAvgPrice)"
                strokeWidth={2}
                name="Средняя цена"
              />
              <Area
                type="monotone"
                dataKey="worstPrice"
                stroke="#f44336"
                fillOpacity={1}
                fill="url(#colorWorstPrice)"
                strokeWidth={2}
                name="Худшая цена"
              />
            </>
          ) : (
            <>
              <Line
                type="monotone"
                dataKey="bestPrice"
                stroke="#4caf50"
                strokeWidth={3}
                dot={{ fill: '#4caf50', strokeWidth: 2, r: 6 }}
                name="Лучшая цена"
              />
              <Line
                type="monotone"
                dataKey="avgPrice"
                stroke="#2196f3"
                strokeWidth={3}
                dot={{ fill: '#2196f3', strokeWidth: 2, r: 6 }}
                name="Средняя цена"
              />
              <Line
                type="monotone"
                dataKey="worstPrice"
                stroke="#f44336"
                strokeWidth={3}
                dot={{ fill: '#f44336', strokeWidth: 2, r: 6 }}
                name="Худшая цена"
              />
            </>
          )}
        </Chart>
      </ResponsiveContainer>
    </Box>
  )
} 