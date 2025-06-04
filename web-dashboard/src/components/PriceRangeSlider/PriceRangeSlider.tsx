import { Box, Typography } from '@mui/material'

interface PriceRangeSliderProps {
  min: number
  max: number
  onChange: (min: number, max: number) => void
}

export default function PriceRangeSlider({ min, max, onChange }: PriceRangeSliderProps) {
  return (
    <Box sx={{ mb: 3 }}>
      <Typography variant="h6" gutterBottom>
        Диапазон цен
      </Typography>
      <Typography variant="body2" color="text.secondary">
        TODO: Реализовать slider для цен
      </Typography>
      <Typography variant="caption" color="text.secondary">
        {min.toLocaleString()} - {max.toLocaleString()} IDR
      </Typography>
    </Box>
  )
} 