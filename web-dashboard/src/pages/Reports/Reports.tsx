import { useState, useEffect } from 'react'
import {
  Box,
  Typography,
  Grid,
  Paper,
  Card,
  CardContent,
  Button,
  Tabs,
  Tab,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Switch,
  FormControlLabel,
  Alert,
  CircularProgress,
  Fab,
  Tooltip
} from '@mui/material'
import {
  Download as DownloadIcon,
  Email as EmailIcon,
  Schedule as ScheduleIcon,
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Send as SendIcon,
  Settings as SettingsIcon,
  GetApp as GetAppIcon,
  Assignment as AssignmentIcon,
  BarChart as BarChartIcon,
  PieChart as PieChartIcon,
  PlayArrow as PlayArrowIcon,
  Stop as StopIcon
} from '@mui/icons-material'
import { format } from 'date-fns'
import { ru } from 'date-fns/locale'

interface ReportTemplate {
  id: string
  name: string
  description: string
  formats: string[]
  sections: string[]
}

interface Subscription {
  id: string
  report_type: string
  frequency: string
  recipients: string[]
  format: string
  enabled: boolean
  last_sent: string | null
  created_at: string
}

interface SchedulerStatus {
  is_running: boolean
  active_subscriptions: number
  total_subscriptions: number
  next_check: string | null
  last_activity: string
}

export default function Reports() {
  const [activeTab, setActiveTab] = useState(0)
  const [templates, setTemplates] = useState<ReportTemplate[]>([])
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([])
  const [schedulerStatus, setSchedulerStatus] = useState<SchedulerStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [generating, setGenerating] = useState(false)

  // Dialogs
  const [createSubDialog, setCreateSubDialog] = useState(false)
  const [emailSettingsDialog, setEmailSettingsDialog] = useState(false)

  // Form states
  const [selectedTemplate, setSelectedTemplate] = useState('')
  const [selectedFormat, setSelectedFormat] = useState('pdf')
  const [newSubscription, setNewSubscription] = useState({
    report_type: '',
    frequency: 'weekly',
    recipients: [''],
    format: 'pdf',
    enabled: true
  })
  
  const [emailSettings, setEmailSettings] = useState({
    smtp_server: '',
    smtp_port: 587,
    username: '',
    password: '',
    use_tls: true,
    sender_name: 'Monito System'
  })

  // Mock данные для начала
  useEffect(() => {
    loadTemplates()
    loadSubscriptions()
    loadSchedulerStatus()
  }, [])

  const loadTemplates = async () => {
    try {
      const response = await fetch('/api/v1/reports/templates')
      const data = await response.json()
      setTemplates(data.templates || [])
    } catch (error) {
      console.error('Error loading templates:', error)
      // Mock данные
      setTemplates([
        {
          id: 'price_analysis',
          name: 'Анализ Цен',
          description: 'Подробный анализ цен, трендов и экономии по категориям',
          formats: ['pdf', 'excel'],
          sections: ['Основные показатели', 'Топ категории', 'Тренды цен', 'Рекомендации']
        },
        {
          id: 'supplier_performance',
          name: 'Производительность Поставщиков',
          description: 'Оценка эффективности поставщиков и их рейтинги',
          formats: ['pdf', 'excel'],
          sections: ['Рейтинги поставщиков', 'Статистика товаров', 'Надежность доставки']
        }
      ])
    }
  }

  const loadSubscriptions = async () => {
    try {
      const response = await fetch('/api/v1/reports/subscriptions')
      if (response.ok) {
        const data = await response.json()
        setSubscriptions(data)
      }
    } catch (error) {
      console.error('Error loading subscriptions:', error)
    }
  }

  const loadSchedulerStatus = async () => {
    try {
      const response = await fetch('/api/v1/reports/scheduler/status')
      if (response.ok) {
        const data = await response.json()
        setSchedulerStatus(data)
      }
    } catch (error) {
      console.error('Error loading scheduler status:', error)
    }
  }

  const generateReport = async (templateId: string, format: string) => {
    setGenerating(true)
    try {
      const response = await fetch('/api/v1/reports/download', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          report_type: templateId,
          format: format,
          include_charts: true
        })
      })

      if (response.ok) {
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `monito_${templateId}_${new Date().toISOString().slice(0, 10)}.${format}`
        document.body.appendChild(a)
        a.click()
        a.remove()
        window.URL.revokeObjectURL(url)
      } else {
        alert('Ошибка генерации отчета')
      }
    } catch (error) {
      console.error('Error generating report:', error)
      alert('Ошибка генерации отчета')
    } finally {
      setGenerating(false)
    }
  }

  const createSubscription = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/v1/reports/subscriptions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newSubscription)
      })

      if (response.ok) {
        setCreateSubDialog(false)
        loadSubscriptions()
        setNewSubscription({
          report_type: '',
          frequency: 'weekly',
          recipients: [''],
          format: 'pdf',
          enabled: true
        })
      } else {
        alert('Ошибка создания подписки')
      }
    } catch (error) {
      console.error('Error creating subscription:', error)
      alert('Ошибка создания подписки')
    } finally {
      setLoading(false)
    }
  }

  const deleteSubscription = async (id: string) => {
    if (!confirm('Удалить подписку?')) return

    try {
      const response = await fetch(`/api/v1/reports/subscriptions/${id}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        loadSubscriptions()
      } else {
        alert('Ошибка удаления подписки')
      }
    } catch (error) {
      console.error('Error deleting subscription:', error)
      alert('Ошибка удаления подписки')
    }
  }

  const sendReportNow = async (id: string) => {
    try {
      const response = await fetch(`/api/v1/reports/subscriptions/${id}/send`, {
        method: 'POST'
      })

      if (response.ok) {
        alert('Отчет отправляется...')
      } else {
        alert('Ошибка отправки отчета')
      }
    } catch (error) {
      console.error('Error sending report:', error)
      alert('Ошибка отправки отчета')
    }
  }

  const configureEmail = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/v1/reports/email/settings', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(emailSettings)
      })

      if (response.ok) {
        setEmailSettingsDialog(false)
        alert('Настройки email сохранены')
      } else {
        alert('Ошибка сохранения настроек')
      }
    } catch (error) {
      console.error('Error configuring email:', error)
      alert('Ошибка сохранения настроек')
    } finally {
      setLoading(false)
    }
  }

  const toggleScheduler = async () => {
    try {
      const endpoint = schedulerStatus?.is_running ? 'stop' : 'start'
      const response = await fetch(`/api/v1/reports/scheduler/${endpoint}`, {
        method: 'POST'
      })

      if (response.ok) {
        loadSchedulerStatus()
      }
    } catch (error) {
      console.error('Error toggling scheduler:', error)
    }
  }

  return (
    <Box>
      {/* Заголовок */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            📊 Отчеты и Аналитика
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Генерация отчетов, автоматические подписки и планировщик
          </Typography>
        </Box>

        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<SettingsIcon />}
            onClick={() => setEmailSettingsDialog(true)}
          >
            Email настройки
          </Button>
          
          <Button
            variant={schedulerStatus?.is_running ? "outlined" : "contained"}
            startIcon={schedulerStatus?.is_running ? <StopIcon /> : <PlayArrowIcon />}
            onClick={toggleScheduler}
            color={schedulerStatus?.is_running ? "error" : "success"}
          >
            {schedulerStatus?.is_running ? 'Остановить' : 'Запустить'} планировщик
          </Button>
        </Box>
      </Box>

      {/* Статус планировщика */}
      {schedulerStatus && (
        <Alert 
          severity={schedulerStatus.is_running ? "success" : "warning"} 
          sx={{ mb: 3 }}
        >
          Планировщик: {schedulerStatus.is_running ? 'Работает' : 'Остановлен'} • 
          Активных подписок: {schedulerStatus.active_subscriptions} • 
          Всего подписок: {schedulerStatus.total_subscriptions}
        </Alert>
      )}

      {/* Табы */}
      <Paper sx={{ mb: 3 }}>
        <Tabs value={activeTab} onChange={(_, newValue) => setActiveTab(newValue)}>
          <Tab label="📋 Генерация отчетов" />
          <Tab label="📧 Подписки" />
          <Tab label="📈 История" />
        </Tabs>
      </Paper>

      {/* Контент табов */}
      {activeTab === 0 && (
        <Grid container spacing={3}>
          {templates.map((template) => (
            <Grid item xs={12} md={6} key={template.id}>
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    {template.id === 'price_analysis' ? (
                      <BarChartIcon sx={{ mr: 1, color: 'primary.main' }} />
                    ) : (
                      <PieChartIcon sx={{ mr: 1, color: 'secondary.main' }} />
                    )}
                    <Typography variant="h6">
                      {template.name}
                    </Typography>
                  </Box>

                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    {template.description}
                  </Typography>

                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      Разделы отчета:
                    </Typography>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {template.sections.map((section) => (
                        <Chip key={section} label={section} size="small" />
                      ))}
                    </Box>
                  </Box>

                  <Box sx={{ display: 'flex', gap: 1 }}>
                    {template.formats.map((format) => (
                      <Button
                        key={format}
                        variant="outlined"
                        size="small"
                        startIcon={<DownloadIcon />}
                        onClick={() => generateReport(template.id, format)}
                        disabled={generating}
                      >
                        {format.toUpperCase()}
                      </Button>
                    ))}
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      {activeTab === 1 && (
        <Box>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
            <Typography variant="h6">
              Подписки на автоматические отчеты
            </Typography>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => setCreateSubDialog(true)}
            >
              Создать подписку
            </Button>
          </Box>

          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Тип отчета</TableCell>
                  <TableCell>Частота</TableCell>
                  <TableCell>Получатели</TableCell>
                  <TableCell>Формат</TableCell>
                  <TableCell>Статус</TableCell>
                  <TableCell>Последняя отправка</TableCell>
                  <TableCell>Действия</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {subscriptions.map((sub) => (
                  <TableRow key={sub.id}>
                    <TableCell>{sub.report_type}</TableCell>
                    <TableCell>{sub.frequency}</TableCell>
                    <TableCell>{sub.recipients.length} получателей</TableCell>
                    <TableCell>{sub.format.toUpperCase()}</TableCell>
                    <TableCell>
                      <Chip
                        label={sub.enabled ? 'Активна' : 'Отключена'}
                        color={sub.enabled ? 'success' : 'default'}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      {sub.last_sent 
                        ? format(new Date(sub.last_sent), 'dd.MM.yyyy HH:mm', { locale: ru })
                        : 'Никогда'
                      }
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', gap: 1 }}>
                        <Tooltip title="Отправить сейчас">
                          <IconButton
                            size="small"
                            onClick={() => sendReportNow(sub.id)}
                            disabled={!sub.enabled}
                          >
                            <SendIcon />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Редактировать">
                          <IconButton size="small">
                            <EditIcon />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Удалить">
                          <IconButton
                            size="small"
                            onClick={() => deleteSubscription(sub.id)}
                          >
                            <DeleteIcon />
                          </IconButton>
                        </Tooltip>
                      </Box>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      )}

      {activeTab === 2 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            📈 История отчетов
          </Typography>
          <Typography variant="body2" color="text.secondary">
            История генерации и отправки отчетов будет доступна в следующих версиях.
          </Typography>
        </Paper>
      )}

      {/* FAB для генерации тестовых отчетов */}
      <Tooltip title="Быстрая генерация">
        <Fab
          color="primary"
          sx={{ position: 'fixed', bottom: 16, right: 16 }}
          onClick={() => generateReport('price_analysis', 'pdf')}
          disabled={generating}
        >
          {generating ? <CircularProgress size={24} /> : <GetAppIcon />}
        </Fab>
      </Tooltip>

      {/* Диалог создания подписки */}
      <Dialog open={createSubDialog} onClose={() => setCreateSubDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>📧 Создать подписку на отчет</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <FormControl fullWidth>
              <InputLabel>Тип отчета</InputLabel>
              <Select
                value={newSubscription.report_type}
                onChange={(e) => setNewSubscription({
                  ...newSubscription,
                  report_type: e.target.value
                })}
              >
                {templates.map((template) => (
                  <MenuItem key={template.id} value={template.id}>
                    {template.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControl fullWidth>
              <InputLabel>Частота отправки</InputLabel>
              <Select
                value={newSubscription.frequency}
                onChange={(e) => setNewSubscription({
                  ...newSubscription,
                  frequency: e.target.value
                })}
              >
                <MenuItem value="daily">Ежедневно</MenuItem>
                <MenuItem value="weekly">Еженедельно</MenuItem>
                <MenuItem value="monthly">Ежемесячно</MenuItem>
              </Select>
            </FormControl>

            <FormControl fullWidth>
              <InputLabel>Формат</InputLabel>
              <Select
                value={newSubscription.format}
                onChange={(e) => setNewSubscription({
                  ...newSubscription,
                  format: e.target.value
                })}
              >
                <MenuItem value="pdf">PDF</MenuItem>
                <MenuItem value="excel">Excel</MenuItem>
              </Select>
            </FormControl>

            <TextField
              fullWidth
              label="Email получатели (через запятую)"
              value={newSubscription.recipients.join(', ')}
              onChange={(e) => setNewSubscription({
                ...newSubscription,
                recipients: e.target.value.split(', ').filter(email => email.trim())
              })}
              placeholder="user1@example.com, user2@example.com"
              helperText="Введите email адреса получателей через запятую"
            />

            <FormControlLabel
              control={
                <Switch
                  checked={newSubscription.enabled}
                  onChange={(e) => setNewSubscription({
                    ...newSubscription,
                    enabled: e.target.checked
                  })}
                />
              }
              label="Подписка активна"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateSubDialog(false)}>Отмена</Button>
          <Button 
            onClick={createSubscription}
            variant="contained"
            disabled={loading || !newSubscription.report_type || !newSubscription.recipients.length}
          >
            {loading ? <CircularProgress size={20} /> : 'Создать'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Диалог настроек email */}
      <Dialog open={emailSettingsDialog} onClose={() => setEmailSettingsDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>📧 Настройки Email</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <TextField
              fullWidth
              label="SMTP Server"
              value={emailSettings.smtp_server}
              onChange={(e) => setEmailSettings({
                ...emailSettings,
                smtp_server: e.target.value
              })}
              placeholder="smtp.gmail.com"
            />

            <TextField
              fullWidth
              label="SMTP Port"
              type="number"
              value={emailSettings.smtp_port}
              onChange={(e) => setEmailSettings({
                ...emailSettings,
                smtp_port: parseInt(e.target.value)
              })}
            />

            <TextField
              fullWidth
              label="Username"
              value={emailSettings.username}
              onChange={(e) => setEmailSettings({
                ...emailSettings,
                username: e.target.value
              })}
            />

            <TextField
              fullWidth
              label="Password"
              type="password"
              value={emailSettings.password}
              onChange={(e) => setEmailSettings({
                ...emailSettings,
                password: e.target.value
              })}
            />

            <TextField
              fullWidth
              label="Sender Name"
              value={emailSettings.sender_name}
              onChange={(e) => setEmailSettings({
                ...emailSettings,
                sender_name: e.target.value
              })}
            />

            <FormControlLabel
              control={
                <Switch
                  checked={emailSettings.use_tls}
                  onChange={(e) => setEmailSettings({
                    ...emailSettings,
                    use_tls: e.target.checked
                  })}
                />
              }
              label="Использовать TLS"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEmailSettingsDialog(false)}>Отмена</Button>
          <Button 
            onClick={configureEmail}
            variant="contained"
            disabled={loading}
          >
            {loading ? <CircularProgress size={20} /> : 'Сохранить'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
} 