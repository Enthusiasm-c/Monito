import { Card, CardContent, CardActions, Typography, Button, Chip, Box, Divider } from '@mui/material'
import { TrendingDown as SavingsIcon, Store as StoreIcon, Inventory as StockIcon } from '@mui/icons-material'

interface Product {
  id: number
  name: string
  category: string
  bestPrice: number
  regularPrice: number
  supplier: string
  savings: number
  unit: string
  stock: number
  image: string | null
}

interface ProductCardProps {
  product: Product
}

export default function ProductCard({ product }: ProductCardProps) {
  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('id-ID', {
      style: 'currency',
      currency: 'IDR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(price)
  }

  return (
    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <CardContent sx={{ flexGrow: 1 }}>
        {/* Категория */}
        <Chip 
          label={product.category}
          size="small"
          color="primary"
          variant="outlined"
          sx={{ mb: 2 }}
        />
        
        {/* Название товара */}
        <Typography variant="h6" component="h3" gutterBottom sx={{ fontWeight: 600 }}>
          {product.name}
        </Typography>
        
        {/* Цены */}
        <Box sx={{ mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
            <Typography variant="h5" color="success.main" sx={{ fontWeight: 'bold' }}>
              {formatPrice(product.bestPrice)}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              / {product.unit}
            </Typography>
          </Box>
          
          {product.savings > 0 && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography 
                variant="body2" 
                sx={{ textDecoration: 'line-through' }}
                color="text.secondary"
              >
                {formatPrice(product.regularPrice)}
              </Typography>
              <Chip
                icon={<SavingsIcon />}
                label={`-${product.savings}%`}
                size="small"
                color="success"
                variant="filled"
              />
            </Box>
          )}
        </Box>
        
        <Divider sx={{ my: 2 }} />
        
        {/* Информация о поставщике и остатках */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <StoreIcon fontSize="small" color="action" />
            <Typography variant="body2" color="text.secondary">
              {product.supplier}
            </Typography>
          </Box>
          
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <StockIcon fontSize="small" color="action" />
            <Typography variant="body2" color="text.secondary">
              {product.stock} шт
            </Typography>
          </Box>
        </Box>
        
        {/* Экономия */}
        {product.savings > 0 && (
          <Box sx={{ 
            backgroundColor: 'success.main', 
            color: 'white', 
            p: 1, 
            borderRadius: 1,
            textAlign: 'center',
            mb: 2
          }}>
            <Typography variant="body2" sx={{ fontWeight: 600 }}>
              💰 Экономия: {formatPrice(product.regularPrice - product.bestPrice)}
            </Typography>
          </Box>
        )}
      </CardContent>
      
      <CardActions sx={{ p: 2, pt: 0 }}>
        <Button 
          variant="contained" 
          fullWidth 
          size="large"
          sx={{ fontWeight: 600 }}
        >
          Выбрать поставщика
        </Button>
      </CardActions>
    </Card>
  )
} 