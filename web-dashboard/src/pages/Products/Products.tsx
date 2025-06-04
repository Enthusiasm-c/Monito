import { Box, Typography } from '@mui/material'

export default function Products() {
  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        📦 Products Management
      </Typography>
      <Typography variant="body1" color="text.secondary">
        Управление товарами и их сопоставление между поставщиками
      </Typography>
      {/* TODO: Реализовать управление товарами */}
    </Box>
  )
} 