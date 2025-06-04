import { Box, Typography, CircularProgress } from '@mui/material'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts'

interface SavingsDataPoint {
  category: string
  totalSavings: number
  avgSavingsPercent: number
  productsCount: number
  color: string
}

interface SavingsChartProps {
  data?: SavingsDataPoint[]
  loading?: boolean
  type?: 'bar' | 'pie'
  height?: number
}

// Mock данные для демонстрации
const mockSavingsData: SavingsDataPoint[] = [
  {
    category: 'Напитки',
    totalSavings: 2400000,
    avgSavingsPercent: 15.2,
    productsCount: 45,
    color: '#4CAF50',
  },
  {
    category: 'Продукты',
    totalSavings: 1800000,
    avgSavingsPercent: 12.8,
    productsCount: 32,
    color: '#2196F3',
  },
  {
    category: 'Хоз. товары',
    totalSavings: 1200000,
    avgSavingsPercent: 18.5,
    productsCount: 28,
    color: '#FF9800',
  },
  {
    category: 'Косметика',
    totalSavings: 900000,
    avgSavingsPercent: 14.1,
    productsCount: 22,
    color: '#E91E63',
  },
  {
    category: 'Электроника',
    totalSavings: 600000,
    avgSavingsPercent: 11.3,
    productsCount: 15,
    color: '#9C27B0',
  },
]

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value)
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
          minWidth: 200,
        }}
      >
        <Typography variant="subtitle2" gutterBottom color="primary">
          {data.category}
        </Typography>
        <Typography variant="body2" sx={{ mb: 0.5 }}>
          💰 Общая экономия: {formatCurrency(data.totalSavings)}
        </Typography>
        <Typography variant="body2" sx={{ mb: 0.5 }}>
          📊 Средняя экономия: {data.avgSavingsPercent}%
        </Typography>
        <Typography variant="body2">
          📦 Товаров: {data.productsCount}
        </Typography>
      </Box>
    )
  }
  return null
}

const PieTooltip = ({ active, payload }: any) => {
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
          {data.category}
        </Typography>
        <Typography variant="body2" sx={{ color: data.color }}>
          {formatCurrency(data.totalSavings)} ({data.avgSavingsPercent}%)
        </Typography>
      </Box>
    )
  }
  return null
}

const renderCustomLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }: any) => {
  const RADIAN = Math.PI / 180
  const radius = innerRadius + (outerRadius - innerRadius) * 0.5
  const x = cx + radius * Math.cos(-midAngle * RADIAN)
  const y = cy + radius * Math.sin(-midAngle * RADIAN)

  return (
    <text
      x={x}
      y={y}
      fill="white"
      textAnchor={x > cx ? 'start' : 'end'}
      dominantBaseline="central"
      fontSize="12"
      fontWeight="bold"
    >
      {`${(percent * 100).toFixed(0)}%`}
    </text>
  )
}

export default function SavingsChart({
  data = mockSavingsData,
  loading = false,
  type = 'bar',
  height = 300,
}: SavingsChartProps) {
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

  if (type === 'pie') {
    return (
      <Box sx={{ width: '100%', height }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={renderCustomLabel}
              outerRadius={80}
              fill="#8884d8"
              dataKey="totalSavings"
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip content={<PieTooltip />} />
            <Legend
              verticalAlign="bottom"
              height={36}
              formatter={(value, entry) => (
                <span style={{ color: entry.color }}>{value}</span>
              )}
            />
          </PieChart>
        </ResponsiveContainer>
      </Box>
    )
  }

  return (
    <Box sx={{ width: '100%', height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
          <XAxis
            dataKey="category"
            stroke="#666"
            fontSize={12}
            angle={-45}
            textAnchor="end"
            height={60}
          />
          <YAxis
            stroke="#666"
            fontSize={12}
            tickFormatter={formatCurrency}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend />
          <Bar
            dataKey="totalSavings"
            name="Общая экономия"
            radius={[4, 4, 0, 0]}
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </Box>
  )
} 