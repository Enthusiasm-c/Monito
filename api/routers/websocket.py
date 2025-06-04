from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import HTMLResponse
from typing import List, Dict, Any
import json
import asyncio
import logging
from datetime import datetime, timedelta
import random

from ..dependencies import get_unified_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["WebSocket"])

class ConnectionManager:
    """Менеджер WebSocket соединений для real-time обновлений"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.price_update_task = None
        
    async def connect(self, websocket: WebSocket):
        """Подключение нового клиента"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New WebSocket connection. Total: {len(self.active_connections)}")
        
        # Запускаем задачу обновления цен если это первое соединение
        if len(self.active_connections) == 1:
            await self.start_price_updates()
            
    def disconnect(self, websocket: WebSocket):
        """Отключение клиента"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")
            
        # Останавливаем обновления если нет подключенных клиентов
        if len(self.active_connections) == 0:
            self.stop_price_updates()
            
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Отправка персонального сообщения"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending message to WebSocket: {e}")
            self.disconnect(websocket)
            
    async def broadcast(self, message: Dict[str, Any]):
        """Рассылка сообщения всем подключенным клиентам"""
        if not self.active_connections:
            return
            
        message_text = json.dumps(message, default=str)
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_text)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                disconnected.append(connection)
                
        # Удаляем отключенные соединения
        for connection in disconnected:
            self.disconnect(connection)
            
    async def start_price_updates(self):
        """Запуск задачи периодического обновления цен"""
        logger.info("Starting price updates task")
        self.price_update_task = asyncio.create_task(self._price_update_loop())
        
    def stop_price_updates(self):
        """Остановка задачи обновления цен"""
        if self.price_update_task:
            logger.info("Stopping price updates task")
            self.price_update_task.cancel()
            self.price_update_task = None
            
    async def _price_update_loop(self):
        """Цикл обновления цен каждые 5 секунд"""
        try:
            while True:
                await asyncio.sleep(5)  # Обновляем каждые 5 секунд
                
                # Генерируем случайное обновление цен
                price_update = self._generate_price_update()
                
                await self.broadcast({
                    "type": "price_update",
                    "data": price_update,
                    "timestamp": datetime.now().isoformat()
                })
                
        except asyncio.CancelledError:
            logger.info("Price update task cancelled")
        except Exception as e:
            logger.error(f"Error in price update loop: {e}")
            
    def _generate_price_update(self) -> Dict[str, Any]:
        """Генерирует случайное обновление цен для демонстрации"""
        
        products = [
            "Coca-Cola 330ml",
            "Bintang Beer 620ml", 
            "Jasmine Rice 5kg",
            "Mineral Water 1L",
            "Instant Noodles"
        ]
        
        suppliers = ["Supplier A", "Supplier B", "Supplier C", "Supplier D"]
        
        # Случайный товар
        product = random.choice(products)
        supplier = random.choice(suppliers)
        
        # Генерируем изменение цены (-10% до +15%)
        price_change = random.uniform(-0.10, 0.15)
        old_price = random.randint(10000, 50000)
        new_price = int(old_price * (1 + price_change))
        
        return {
            "product_name": product,
            "supplier": supplier,
            "old_price": old_price,
            "new_price": new_price,
            "price_change_percent": round(price_change * 100, 2),
            "category": random.choice(["Beverages", "Food", "Household"]),
            "updated_at": datetime.now().isoformat()
        }

# Глобальный менеджер соединений
manager = ConnectionManager()

@router.websocket("/connect")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint для real-time обновлений"""
    await manager.connect(websocket)
    
    try:
        # Отправляем приветственное сообщение
        await manager.send_personal_message(
            json.dumps({
                "type": "welcome",
                "message": "Connected to Monito Real-time Updates",
                "timestamp": datetime.now().isoformat()
            }),
            websocket
        )
        
        # Отправляем текущую статистику
        stats_update = await generate_stats_update()
        await manager.send_personal_message(
            json.dumps({
                "type": "stats_update", 
                "data": stats_update,
                "timestamp": datetime.now().isoformat()
            }),
            websocket
        )
        
        # Слушаем сообщения от клиента
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Обрабатываем запросы от клиента
            if message.get("type") == "subscribe":
                subscription = message.get("subscription", "all")
                logger.info(f"Client subscribed to: {subscription}")
                
            elif message.get("type") == "request_stats":
                stats = await generate_stats_update()
                await manager.send_personal_message(
                    json.dumps({
                        "type": "stats_update",
                        "data": stats,
                        "timestamp": datetime.now().isoformat()
                    }),
                    websocket
                )
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

@router.post("/broadcast")
async def broadcast_message(message: Dict[str, Any]):
    """Endpoint для отправки сообщений всем подключенным клиентам"""
    await manager.broadcast({
        "type": "admin_message",
        "data": message,
        "timestamp": datetime.now().isoformat()
    })
    return {"message": "Broadcast sent", "active_connections": len(manager.active_connections)}

@router.get("/connections")
async def get_active_connections():
    """Получение количества активных соединений"""
    return {
        "active_connections": len(manager.active_connections),
        "timestamp": datetime.now().isoformat()
    }

async def generate_stats_update() -> Dict[str, Any]:
    """Генерирует обновление статистики для dashboard"""
    
    # В реальном приложении здесь будут запросы к БД
    return {
        "total_products": random.randint(1200, 1300),
        "total_suppliers": random.randint(20, 25),
        "total_prices": random.randint(5000, 6000),
        "avg_savings": round(random.uniform(14.0, 18.0), 1),
        "updates_today": random.randint(300, 400),
        "api_response_time": random.randint(80, 150),
        "system_health": random.choice(["excellent", "good"]),
        "last_update": datetime.now().isoformat(),
        
        # Дополнительная аналитика
        "price_trends": {
            "trend_direction": random.choice(["up", "down", "stable"]),
            "trend_percent": round(random.uniform(-5.0, 5.0), 2)
        },
        
        "top_categories": [
            {"name": "Beverages", "savings": round(random.uniform(12, 18), 1)},
            {"name": "Food", "savings": round(random.uniform(10, 16), 1)},
            {"name": "Household", "savings": round(random.uniform(15, 20), 1)}
        ]
    }

# Test HTML page для тестирования WebSocket
@router.get("/test")
async def websocket_test_page():
    """Тестовая HTML страница для проверки WebSocket"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Monito WebSocket Test</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 800px; }
            .messages { border: 1px solid #ccc; height: 400px; overflow-y: scroll; padding: 10px; margin: 10px 0; }
            .message { margin: 5px 0; padding: 5px; border-radius: 3px; }
            .price-update { background-color: #e8f5e8; }
            .stats-update { background-color: #e8f0ff; }
            .welcome { background-color: #fff8e1; }
            input, button { margin: 5px; padding: 8px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Monito WebSocket Test</h1>
            <div>
                <button onclick="connect()">Connect</button>
                <button onclick="disconnect()">Disconnect</button>
                <button onclick="requestStats()">Request Stats</button>
                <span id="status">Disconnected</span>
            </div>
            <div class="messages" id="messages"></div>
        </div>

        <script>
            let ws = null;
            
            function connect() {
                if (ws) return;
                
                ws = new WebSocket("ws://localhost:8000/ws/connect");
                
                ws.onopen = function(event) {
                    document.getElementById('status').innerText = 'Connected';
                    addMessage('Connected to WebSocket', 'welcome');
                };
                
                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    addMessage(JSON.stringify(data, null, 2), data.type);
                };
                
                ws.onclose = function(event) {
                    document.getElementById('status').innerText = 'Disconnected';
                    addMessage('WebSocket closed', 'welcome');
                    ws = null;
                };
                
                ws.onerror = function(error) {
                    addMessage('Error: ' + error, 'error');
                };
            }
            
            function disconnect() {
                if (ws) {
                    ws.close();
                }
            }
            
            function requestStats() {
                if (ws) {
                    ws.send(JSON.stringify({type: 'request_stats'}));
                }
            }
            
            function addMessage(message, type) {
                const messages = document.getElementById('messages');
                const div = document.createElement('div');
                div.className = 'message ' + (type || '');
                div.innerHTML = '<strong>' + new Date().toLocaleTimeString() + '</strong><br>' + 
                               '<pre>' + message + '</pre>';
                messages.appendChild(div);
                messages.scrollTop = messages.scrollHeight;
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content) 