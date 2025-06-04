# 🌐 Monito Web Dashboard

Modern web dashboard for Monito Unified Price Management System v3.0

## 🚀 Features

- **🏝️ Unified Catalog** - Search products with best prices from all Bali suppliers
- **📊 Real-time Analytics** - Price trends and statistics dashboard  
- **🔍 Advanced Search** - Filter by category, supplier, price range
- **💰 Price Comparison** - Automatic price comparison and savings calculation
- **📱 Responsive Design** - Works on desktop, tablet and mobile
- **🎨 Material-UI** - Modern and beautiful interface
- **⚡ Fast Performance** - Built with React + TypeScript + Vite

## 🛠️ Tech Stack

- **Frontend**: React 19 + TypeScript
- **UI Framework**: Material-UI (MUI) v6
- **Build Tool**: Vite 6
- **State Management**: Zustand
- **HTTP Client**: Axios + React Query
- **Charts**: Recharts
- **Forms**: React Hook Form + Zod validation
- **Routing**: React Router v6
- **Animations**: Framer Motion

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ 
- npm or yarn
- Monito API server running (see ../api/)

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Development

```bash
# Run with hot reload
npm run dev

# Run tests
npm run test

# Run tests with UI
npm run test:ui

# Lint code
npm run lint
```

## 🌐 Environment Setup

Create `.env` file in the project root:

```env
# API Configuration
VITE_API_BASE_URL=http://localhost:8000
VITE_API_TIMEOUT=30000

# Features
VITE_ENABLE_ANALYTICS=true
VITE_ENABLE_MOCK_DATA=false

# UI Configuration  
VITE_APP_TITLE=Monito Unified Dashboard
VITE_ITEMS_PER_PAGE=20
```

## 📖 Pages & Features

### 🏠 Dashboard
- System overview and statistics
- Real-time price trends chart
- Top deals with maximum savings
- Recent activity feed
- Quick action cards

### 🏪 Unified Catalog
- Advanced product search with filters
- Category-based browsing
- Price comparison from all suppliers
- Savings calculation and highlighting
- Mobile-responsive product cards

### 📦 Products Management
- Product inventory overview
- Product matching between suppliers
- Bulk operations and updates
- Category management

### 🏬 Suppliers Management  
- Supplier performance analytics
- Reliability scoring
- Contact information management
- Price update history

### 📊 Analytics
- Price trend analysis
- Market insights dashboard
- Supplier performance reports
- Savings opportunity identification

### ⚙️ Settings
- System configuration
- User preferences
- API endpoint management
- Cache and performance settings

## 🎨 UI Components

### Core Components
- `Layout` - Main application layout with sidebar
- `StatCard` - Statistical information cards
- `ProductCard` - Product display with price comparison
- `PriceChart` - Interactive price trend charts

### Feature Components
- `TopDeals` - Best savings opportunities
- `RecentActivity` - System activity feed
- `CategoryFilter` - Product category filtering
- `PriceRangeSlider` - Price range selection

## 🔌 API Integration

The dashboard integrates with Monito Unified API:

```typescript
// Example API calls
const searchProducts = async (query: string) => {
  const response = await axios.get('/api/v1/catalog/search', {
    params: { query, limit: 20 }
  })
  return response.data
}

const getTopDeals = async () => {
  const response = await axios.get('/api/v1/catalog/top-deals')
  return response.data
}
```

## 📱 Responsive Design

- **Desktop**: Full featured layout with sidebar
- **Tablet**: Responsive grid with collapsible sidebar  
- **Mobile**: Stack layout with bottom navigation

## 🚀 Performance

- **Code Splitting**: Automatic route-based splitting
- **Lazy Loading**: Components loaded on demand
- **Caching**: React Query for API response caching
- **Bundle Size**: Optimized with tree shaking

## 🧪 Testing

```bash
# Unit tests
npm run test

# Component testing
npm run test:ui

# E2E tests (future)
npm run test:e2e
```

## 🚢 Deployment

### Production Build

```bash
npm run build
```

### Docker Deployment

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "run", "preview"]
```

### Environment Variables

Production environment variables:

```env
VITE_API_BASE_URL=https://api.monito.bali
VITE_ENABLE_ANALYTICS=true
VITE_ENABLE_MOCK_DATA=false
```

## 🔧 Development Workflow

1. **Feature Development**
   - Create feature branch
   - Implement component with TypeScript
   - Add tests and documentation
   - Create pull request

2. **Code Standards**
   - TypeScript strict mode
   - ESLint + Prettier formatting
   - Component-based architecture
   - Material-UI design system

3. **State Management**
   - Zustand for global state
   - React Query for server state
   - Local state with useState/useReducer

## 📈 Roadmap

- [ ] Real-time WebSocket integration
- [ ] Advanced filtering and search
- [ ] Export functionality (PDF, Excel)
- [ ] User authentication and permissions
- [ ] Multi-language support (ID/EN)
- [ ] Dark mode theme
- [ ] Offline mode with service workers
- [ ] Mobile app (React Native)

## 🐛 Troubleshooting

### Common Issues

1. **API Connection Error**
   - Check VITE_API_BASE_URL in .env
   - Ensure API server is running
   - Verify CORS settings

2. **Build Errors**
   - Clear node_modules and reinstall
   - Check TypeScript errors
   - Verify all imports

3. **Performance Issues**
   - Enable React DevTools Profiler
   - Check for unnecessary re-renders
   - Optimize heavy computations

## 📄 License

Part of Monito Unified System v3.0

---

**🏝️ Built for Bali Suppliers - Powered by Modern Web Technologies**
