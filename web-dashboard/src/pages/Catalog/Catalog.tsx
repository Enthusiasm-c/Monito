import { useState } from 'react'
import {
  Box,
  Typography,
  TextField,
  Button,
  Grid,
  Paper,
  Chip,
  InputAdornment,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Card,
  CardContent,
  IconButton,
  Divider,
} from '@mui/material'
import {
  Search as SearchIcon,
  FilterList as FilterIcon,
  TrendingDown as TrendingDownIcon,
  Store as StoreIcon,
  LocalOffer as OfferIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material'

import ProductCard from '../../components/ProductCard/ProductCard'
import CategoryFilter from '../../components/CategoryFilter/CategoryFilter'
import PriceRangeSlider from '../../components/PriceRangeSlider/PriceRangeSlider'

interface SearchFilters {
  query: string
  category: string
  priceMin: number
  priceMax: number
  supplier: string
  sortBy: string
}

export default function Catalog() {
  const [filters, setFilters] = useState<SearchFilters>({
    query: '',
    category: '',
    priceMin: 0,
    priceMax: 1000000,
    supplier: '',
    sortBy: 'best_price',
  })

  const [isLoading, setIsLoading] = useState(false)

  const handleSearch = () => {
    setIsLoading(true)
    // TODO: Интеграция с API
    setTimeout(() => setIsLoading(false), 1000)
  }

  const handleFilterChange = (key: keyof SearchFilters, value: string | number) => {
    setFilters(prev => ({ ...prev, [key]: value }))
  }

  const mockProducts = [
    {
      id: 1,
      name: 'Coca-Cola 330ml',
      category: 'Beverages',
      bestPrice: 13500,
      regularPrice: 15000,
      supplier: 'Supplier A',
      savings: 10,
      unit: 'piece',
      stock: 150,
      image: null,
    },
    {
      id: 2,
      name: 'Bintang Beer 620ml',
      category: 'Beverages',
      bestPrice: 25000,
      regularPrice: 28000,
      supplier: 'Supplier B',
      savings: 11,
      unit: 'piece',
      stock: 75,
      image: null,
    },
    {
      id: 3,
      name: 'Jasmine Rice 5kg',
      category: 'Food',
      bestPrice: 125000,
      regularPrice: 150000,
      supplier: 'Supplier C',
      savings: 17,
      unit: 'bag',
      stock: 30,
      image: null,
    },
  ]

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom sx={{ mb: 2 }}>
        🏪 Unified Catalog
      </Typography>
      
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Поиск товаров с лучшими ценами от всех поставщиков острова Бали
      </Typography>

      {/* Поисковая панель */}
      <Paper sx={{ p: 3, mb: 4 }}>
        <Grid container spacing={3} alignItems="center">
          <Grid item xs={12} md={4}>
            <TextField
              fullWidth
              label="Поиск товаров"
              value={filters.query}
              onChange={(e) => handleFilterChange('query', e.target.value)}
              placeholder="Введите название товара..."
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon />
                  </InputAdornment>
                ),
              }}
            />
          </Grid>
          
          <Grid item xs={12} md={2}>
            <FormControl fullWidth>
              <InputLabel>Категория</InputLabel>
              <Select
                value={filters.category}
                label="Категория"
                onChange={(e) => handleFilterChange('category', e.target.value)}
              >
                <MenuItem value="">Все категории</MenuItem>
                <MenuItem value="beverages">Напитки</MenuItem>
                <MenuItem value="food">Продукты</MenuItem>
                <MenuItem value="household">Хоз. товары</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          
          <Grid item xs={12} md={2}>
            <FormControl fullWidth>
              <InputLabel>Поставщик</InputLabel>
              <Select
                value={filters.supplier}
                label="Поставщик"
                onChange={(e) => handleFilterChange('supplier', e.target.value)}
              >
                <MenuItem value="">Все поставщики</MenuItem>
                <MenuItem value="supplier_a">Supplier A</MenuItem>
                <MenuItem value="supplier_b">Supplier B</MenuItem>
                <MenuItem value="supplier_c">Supplier C</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          
          <Grid item xs={12} md={2}>
            <FormControl fullWidth>
              <InputLabel>Сортировка</InputLabel>
              <Select
                value={filters.sortBy}
                label="Сортировка"
                onChange={(e) => handleFilterChange('sortBy', e.target.value)}
              >
                <MenuItem value="best_price">Лучшая цена</MenuItem>
                <MenuItem value="savings">Максимальная экономия</MenuItem>
                <MenuItem value="name">По названию</MenuItem>
                <MenuItem value="category">По категории</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          
          <Grid item xs={12} md={2}>
            <Button
              fullWidth
              variant="contained"
              size="large"
              onClick={handleSearch}
              disabled={isLoading}
              startIcon={<SearchIcon />}
            >
              {isLoading ? 'Поиск...' : 'Найти'}
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {/* Активные фильтры */}
      <Box sx={{ mb: 3, display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'center' }}>
        <Typography variant="body2" color="text.secondary">
          Активные фильтры:
        </Typography>
        {filters.query && (
          <Chip
            label={`Поиск: "${filters.query}"`}
            onDelete={() => handleFilterChange('query', '')}
            size="small"
          />
        )}
        {filters.category && (
          <Chip
            label={`Категория: ${filters.category}`}
            onDelete={() => handleFilterChange('category', '')}
            size="small"
          />
        )}
        {filters.supplier && (
          <Chip
            label={`Поставщик: ${filters.supplier}`}
            onDelete={() => handleFilterChange('supplier', '')}
            size="small"
          />
        )}
        <IconButton size="small" onClick={() => setFilters({
          query: '',
          category: '',
          priceMin: 0,
          priceMax: 1000000,
          supplier: '',
          sortBy: 'best_price',
        })}>
          <RefreshIcon />
        </IconButton>
      </Box>

      {/* Статистика поиска */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <StoreIcon sx={{ fontSize: 40, color: 'primary.main', mb: 1 }} />
              <Typography variant="h5" component="div">
                {mockProducts.length}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Товаров найдено
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <TrendingDownIcon sx={{ fontSize: 40, color: 'success.main', mb: 1 }} />
              <Typography variant="h5" component="div">
                12.7%
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Средняя экономия
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <OfferIcon sx={{ fontSize: 40, color: 'warning.main', mb: 1 }} />
              <Typography variant="h5" component="div">
                5
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Поставщиков
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent sx={{ textAlign: 'center' }}>
              <Typography variant="h5" component="div" color="primary.main">
                4.2★
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Рейтинг качества
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Divider sx={{ mb: 4 }} />

      {/* Результаты поиска */}
      <Typography variant="h6" gutterBottom>
        📦 Результаты поиска ({mockProducts.length})
      </Typography>
      
      <Grid container spacing={3}>
        {mockProducts.map((product) => (
          <Grid item xs={12} sm={6} lg={4} key={product.id}>
            <ProductCard product={product} />
          </Grid>
        ))}
      </Grid>

      {/* Боковые фильтры (скрыты на мобильных) */}
      <Box sx={{ display: { xs: 'none', lg: 'block' } }}>
        <Paper sx={{ p: 3, position: 'fixed', right: 24, top: 120, width: 280, maxHeight: 'calc(100vh - 140px)', overflow: 'auto' }}>
          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <FilterIcon />
            Дополнительные фильтры
          </Typography>
          
          <CategoryFilter />
          <PriceRangeSlider
            min={filters.priceMin}
            max={filters.priceMax}
            onChange={(min: number, max: number) => {
              handleFilterChange('priceMin', min)
              handleFilterChange('priceMax', max)
            }}
          />
        </Paper>
      </Box>
    </Box>
  )
} 