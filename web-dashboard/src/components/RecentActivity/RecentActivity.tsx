import { Box, List, ListItem, ListItemText, Typography, Chip } from '@mui/material'

const mockActivities = [
  { action: 'Обновлены цены', supplier: 'Supplier A', time: '2 мин назад', type: 'price' },
  { action: 'Добавлен новый товар', supplier: 'Supplier B', time: '15 мин назад', type: 'product' },
  { action: 'Создан отчет', supplier: 'System', time: '1 час назад', type: 'report' },
]

export default function RecentActivity() {
  return (
    <Box>
      <List>
        {mockActivities.map((activity, index) => (
          <ListItem key={index} divider>
            <ListItemText
              primary={activity.action}
              secondary={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="caption" color="text.secondary">
                    {activity.supplier}
                  </Typography>
                  <Chip label={activity.time} size="small" variant="outlined" />
                </Box>
              }
            />
          </ListItem>
        ))}
      </List>
    </Box>
  )
} 