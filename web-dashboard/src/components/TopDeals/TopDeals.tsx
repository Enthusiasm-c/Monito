import { Box, Typography, List, ListItem, ListItemText, Chip } from '@mui/material'

const mockDeals = [
  { name: 'Coca-Cola 330ml', savings: 15, price: '13,500 IDR' },
  { name: 'Jasmine Rice 5kg', savings: 17, price: '125,000 IDR' },
  { name: 'Bintang Beer 620ml', savings: 11, price: '25,000 IDR' },
]

export default function TopDeals() {
  return (
    <Box>
      <List>
        {mockDeals.map((deal, index) => (
          <ListItem key={index} divider>
            <ListItemText
              primary={deal.name}
              secondary={deal.price}
            />
            <Chip
              label={`-${deal.savings}%`}
              color="success"
              size="small"
            />
          </ListItem>
        ))}
      </List>
    </Box>
  )
} 