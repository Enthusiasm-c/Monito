import type { ReactNode } from 'react'
import { Card, CardContent, Typography, Box, Chip } from '@mui/material'

interface StatCardProps {
  title: string
  value: string
  icon: ReactNode
  color: 'primary' | 'secondary' | 'success' | 'info' | 'warning' | 'error'
  subtitle?: string
  trend?: string
}

export default function StatCard({ title, value, icon, color, subtitle, trend }: StatCardProps) {
  return (
    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <CardContent sx={{ flexGrow: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Box sx={{ color: `${color}.main` }}>
            {icon}
          </Box>
          {trend && (
            <Chip 
              label={trend}
              size="small"
              color={color}
              variant="outlined"
            />
          )}
        </Box>
        
        <Typography variant="h4" component="div" sx={{ fontWeight: 'bold', mb: 1 }}>
          {value}
        </Typography>
        
        <Typography variant="h6" color="text.secondary" gutterBottom>
          {title}
        </Typography>
        
        {subtitle && (
          <Typography variant="body2" color="text.secondary">
            {subtitle}
          </Typography>
        )}
      </CardContent>
    </Card>
  )
} 