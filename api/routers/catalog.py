"""
=============================================================================
MONITO API CATALOG ROUTER
=============================================================================
Версия: 3.0
Цель: Роутер для unified каталога товаров с лучшими ценами
=============================================================================
"""

from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Request, Depends, Query, HTTPException
from pydantic import BaseModel, Field

from api.schemas.base import PaginatedResponse
from modules.adapters.legacy_integration_adapter import LegacyIntegrationAdapter
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

def get_integration_adapter(request: Request) -> LegacyIntegrationAdapter:
    """Dependency для получения integration adapter"""
    return request.app.state.integration_adapter

# ============================================================================= 
# PYDANTIC SCHEMAS для Catalog API
# =============================================================================

class CatalogProductResponse(BaseModel):
    """Схема товара в unified каталоге"""
    
    product_id: str = Field(description="ID товара в unified системе")
    standard_name: str = Field(description="Стандартизованное название товара")
    brand: Optional[str] = Field(description="Бренд товара")
    category: str = Field(description="Категория товара")
    description: Optional[str] = Field(description="Описание товара")
    
    # Информация о лучшей цене
    best_price: float = Field(description="Лучшая цена среди всех поставщиков")
    best_supplier: str = Field(description="Поставщик с лучшей ценой")
    unit: str = Field(description="Единица измерения")
    
    # Статистика по ценам
    price_count: int = Field(description="Количество доступных цен")
    price_min: float = Field(description="Минимальная цена")
    price_max: float = Field(description="Максимальная цена")
    price_avg: float = Field(description="Средняя цена")
    
    # Информация об экономии
    savings_amount: Optional[float] = Field(description="Сумма экономии (от средней цены)")
    savings_percentage: Optional[float] = Field(description="Процент экономии")
    
    # Рейтинги и рекомендации
    supplier_reliability: Optional[float] = Field(description="Надежность лучшего поставщика")
    recommendation_score: Optional[float] = Field(description="Оценка рекомендации к покупке")
    
    class Config:
        schema_extra = {
            "example": {
                "product_id": "prod_12345",
                "standard_name": "Coca-Cola 330ml Can",
                "brand": "Coca-Cola",
                "category": "beverages",
                "description": "Coca-Cola Original Taste 330ml Aluminum Can",
                "best_price": 8500.0,
                "best_supplier": "PT Global Supply Bali",
                "unit": "pcs",
                "price_count": 5,
                "price_min": 8500.0,
                "price_max": 12000.0,
                "price_avg": 9800.0,
                "savings_amount": 1300.0,
                "savings_percentage": 13.3,
                "supplier_reliability": 4.8,
                "recommendation_score": 0.92
            }
        }

class CatalogSearchRequest(BaseModel):
    """Запрос поиска по каталогу"""
    
    query: Optional[str] = Field(None, description="Поисковый запрос")
    category: Optional[str] = Field(None, description="Фильтр по категории")
    brand: Optional[str] = Field(None, description="Фильтр по бренду")
    supplier: Optional[str] = Field(None, description="Фильтр по поставщику")
    price_min: Optional[float] = Field(None, ge=0, description="Минимальная цена")
    price_max: Optional[float] = Field(None, ge=0, description="Максимальная цена")
    sort_by: str = Field("best_price", description="Поле для сортировки")
    sort_order: str = Field("asc", description="Порядок сортировки (asc/desc)")
    
    class Config:
        schema_extra = {
            "example": {
                "query": "coca cola",
                "category": "beverages",
                "price_min": 5000,
                "price_max": 15000,
                "sort_by": "best_price",
                "sort_order": "asc"
            }
        }

class TopDealResponse(BaseModel):
    """Схема топового предложения"""
    
    product_name: str = Field(description="Название товара")
    product_id: str = Field(description="ID товара")
    category: str = Field(description="Категория")
    best_price: float = Field(description="Лучшая цена")
    regular_price: float = Field(description="Обычная цена")
    savings_amount: float = Field(description="Сумма экономии")
    savings_percentage: float = Field(description="Процент экономии")
    supplier: str = Field(description="Поставщик")
    deal_confidence: float = Field(description="Надежность предложения")
    
    class Config:
        schema_extra = {
            "example": {
                "product_name": "Bintang Beer 330ml",
                "product_id": "prod_67890",
                "category": "beverages",
                "best_price": 15000.0,
                "regular_price": 18000.0,
                "savings_amount": 3000.0,
                "savings_percentage": 16.7,
                "supplier": "UD Rahayu Bali",
                "deal_confidence": 0.85
            }
        }

class ProcurementRecommendationRequest(BaseModel):
    """Запрос рекомендаций по закупкам"""
    
    required_products: List[Dict[str, Any]] = Field(description="Список требуемых товаров")
    budget_limit: Optional[float] = Field(None, description="Лимит бюджета")
    preferred_suppliers: Optional[List[str]] = Field(None, description="Предпочтительные поставщики")
    optimize_for: str = Field("cost", description="Критерий оптимизации (cost/quality/reliability)")
    
    class Config:
        schema_extra = {
            "example": {
                "required_products": [
                    {"name": "Coca-Cola 330ml", "quantity": 100},
                    {"name": "Bintang Beer 330ml", "quantity": 50}
                ],
                "budget_limit": 2000000,
                "preferred_suppliers": ["PT Global Supply"],
                "optimize_for": "cost"
            }
        }

# =============================================================================
# CATALOG ENDPOINTS
# =============================================================================

@router.get("/search",
           response_model=PaginatedResponse[CatalogProductResponse],
           summary="🔍 Поиск по unified каталогу",
           description="Поиск товаров в unified каталоге с автоматическим сравнением цен от всех поставщиков")
async def search_catalog(
    request: Request,
    integration_adapter: LegacyIntegrationAdapter = Depends(get_integration_adapter),
    query: Optional[str] = Query(None, description="Поисковый запрос"),
    category: Optional[str] = Query(None, description="Фильтр по категории"),
    brand: Optional[str] = Query(None, description="Фильтр по бренду"),
    supplier: Optional[str] = Query(None, description="Фильтр по поставщику"),
    price_min: Optional[float] = Query(None, ge=0, description="Минимальная цена"),
    price_max: Optional[float] = Query(None, ge=0, description="Максимальная цена"),
    sort_by: str = Query("best_price", description="Поле для сортировки"),
    sort_order: str = Query("asc", description="Порядок сортировки"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    limit: int = Query(50, ge=1, le=1000, description="Количество элементов на странице")
) -> PaginatedResponse[CatalogProductResponse]:
    """
    Поиск товаров в unified каталоге
    
    Функциональность:
    - Поиск по названию, бренду, категории
    - Автоматическое сравнение цен от всех поставщиков
    - Показ лучших предложений и экономии
    - Фильтрация и сортировка результатов
    - Пагинация больших результатов
    
    Returns:
        Список товаров с лучшими ценами и статистикой
    """
    logger.info(f"Catalog search: query='{query}', category='{category}', filters={{'price_min': {price_min}, 'price_max': {price_max}}}")
    
    try:
        # Формируем параметры поиска
        search_query = query or ""
        
        # Получаем товары из unified системы
        if search_query:
            master_products = integration_adapter.db_manager.search_master_products(search_query, limit=limit*2)
        else:
            # Получаем все товары если нет поискового запроса
            master_products = integration_adapter.db_manager.search_master_products("", limit=limit*2)
        
        catalog_products = []
        
        for product in master_products:
            # Получаем все цены для товара
            prices = integration_adapter.db_manager.get_current_prices_for_product(str(product.product_id))
            
            if not prices:
                continue
            
            # Применяем фильтры
            if category and product.category.lower() != category.lower():
                continue
            if brand and product.brand and product.brand.lower() != brand.lower():
                continue
            if supplier:
                supplier_prices = [p for p in prices if p.supplier_name.lower() == supplier.lower()]
                if not supplier_prices:
                    continue
                prices = supplier_prices
            
            # Фильтруем по ценам
            if price_min is not None:
                prices = [p for p in prices if p.price >= price_min]
            if price_max is not None:
                prices = [p for p in prices if p.price <= price_max]
            
            if not prices:
                continue
            
            # Рассчитываем статистику цен
            price_values = [p.price for p in prices]
            best_price = min(price_values)
            price_max_val = max(price_values)
            price_avg = sum(price_values) / len(price_values)
            
            # Находим лучшего поставщика
            best_price_obj = min(prices, key=lambda p: p.price)
            
            # Рассчитываем экономию
            savings_amount = price_avg - best_price if price_avg > best_price else 0
            savings_percentage = (savings_amount / price_avg * 100) if price_avg > 0 else 0
            
            # Создаем объект каталога
            catalog_product = CatalogProductResponse(
                product_id=str(product.product_id),
                standard_name=product.standard_name,
                brand=product.brand or "Unknown",
                category=product.category,
                description=product.description,
                best_price=best_price,
                best_supplier=best_price_obj.supplier_name,
                unit=best_price_obj.unit,
                price_count=len(prices),
                price_min=best_price,
                price_max=price_max_val,
                price_avg=price_avg,
                savings_amount=savings_amount,
                savings_percentage=savings_percentage,
                supplier_reliability=4.5,  # Упрощенно, можно улучшить
                recommendation_score=0.8 if savings_percentage > 10 else 0.6
            )
            
            catalog_products.append(catalog_product)
        
        # Сортировка
        reverse_sort = sort_order.lower() == "desc"
        if sort_by == "best_price":
            catalog_products.sort(key=lambda x: x.best_price, reverse=reverse_sort)
        elif sort_by == "savings_percentage":
            catalog_products.sort(key=lambda x: x.savings_percentage or 0, reverse=reverse_sort)
        elif sort_by == "standard_name":
            catalog_products.sort(key=lambda x: x.standard_name, reverse=reverse_sort)
        
        # Пагинация
        offset = (page - 1) * limit
        paginated_products = catalog_products[offset:offset + limit]
        total = len(catalog_products)
        
        logger.info(f"Catalog search completed: found {total} products, page {page}/{(total + limit - 1) // limit}")
        
        return PaginatedResponse.create(
            data=paginated_products,
            page=page,
            limit=limit,
            total=total,
            message=f"Found {total} products matching your criteria"
        )
        
    except Exception as e:
        logger.error(f"Catalog search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/top-deals",
           response_model=List[TopDealResponse],
           summary="🔥 Топовые предложения",
           description="Лучшие предложения с максимальной экономией")
async def get_top_deals(
    request: Request,
    integration_adapter: LegacyIntegrationAdapter = Depends(get_integration_adapter),
    limit: int = Query(20, ge=1, le=100, description="Количество топовых предложений"),
    category: Optional[str] = Query(None, description="Фильтр по категории")
) -> List[TopDealResponse]:
    """
    Получение топовых предложений с максимальной экономией
    
    Показывает товары где разница между лучшей и средней ценой максимальна
    
    Returns:
        Список лучших предложений с расчетом экономии
    """
    logger.info(f"Top deals requested: limit={limit}, category={category}")
    
    try:
        # Получаем все товары
        master_products = integration_adapter.db_manager.search_master_products("", limit=200)
        
        top_deals = []
        
        for product in master_products:
            # Фильтр по категории
            if category and product.category.lower() != category.lower():
                continue
            
            # Получаем цены
            prices = integration_adapter.db_manager.get_current_prices_for_product(str(product.product_id))
            
            if len(prices) < 2:  # Нужно минимум 2 цены для сравнения
                continue
            
            price_values = [p.price for p in prices]
            best_price = min(price_values)
            avg_price = sum(price_values) / len(price_values)
            
            # Рассчитываем экономию
            savings_amount = avg_price - best_price
            savings_percentage = (savings_amount / avg_price * 100) if avg_price > 0 else 0
            
            # Только предложения с экономией больше 5%
            if savings_percentage < 5:
                continue
            
            best_price_obj = min(prices, key=lambda p: p.price)
            
            deal = TopDealResponse(
                product_name=product.standard_name,
                product_id=str(product.product_id),
                category=product.category,
                best_price=best_price,
                regular_price=avg_price,
                savings_amount=savings_amount,
                savings_percentage=savings_percentage,
                supplier=best_price_obj.supplier_name,
                deal_confidence=min(0.9, 0.5 + (savings_percentage / 100))  # Простая формула
            )
            
            top_deals.append(deal)
        
        # Сортируем по проценту экономии
        top_deals.sort(key=lambda x: x.savings_percentage, reverse=True)
        
        # Ограничиваем количество
        top_deals = top_deals[:limit]
        
        logger.info(f"Top deals found: {len(top_deals)} deals")
        
        return top_deals
        
    except Exception as e:
        logger.error(f"Top deals request failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get top deals: {str(e)}")

@router.get("/categories",
           response_model=Dict[str, Any],
           summary="📋 Категории товаров",
           description="Список всех категорий товаров с статистикой")
async def get_categories(
    request: Request,
    integration_adapter: LegacyIntegrationAdapter = Depends(get_integration_adapter)
) -> Dict[str, Any]:
    """
    Получение списка категорий товаров со статистикой
    
    Returns:
        Список категорий с количеством товаров и статистикой цен
    """
    logger.info("Categories list requested")
    
    try:
        # Получаем все товары
        master_products = integration_adapter.db_manager.search_master_products("", limit=1000)
        
        # Группируем по категориям
        categories = {}
        
        for product in master_products:
            category = product.category or "uncategorized"
            
            if category not in categories:
                categories[category] = {
                    "name": category,
                    "product_count": 0,
                    "supplier_count": set(),
                    "price_range": {"min": float("inf"), "max": 0},
                    "avg_price": 0,
                    "total_prices": []
                }
            
            categories[category]["product_count"] += 1
            
            # Получаем цены для статистики
            prices = integration_adapter.db_manager.get_current_prices_for_product(str(product.product_id))
            
            for price in prices:
                categories[category]["supplier_count"].add(price.supplier_name)
                categories[category]["total_prices"].append(price.price)
                
                # Обновляем диапазон цен
                if price.price < categories[category]["price_range"]["min"]:
                    categories[category]["price_range"]["min"] = price.price
                if price.price > categories[category]["price_range"]["max"]:
                    categories[category]["price_range"]["max"] = price.price
        
        # Финализируем статистику
        result_categories = []
        for cat_name, cat_data in categories.items():
            if cat_data["total_prices"]:
                cat_data["avg_price"] = sum(cat_data["total_prices"]) / len(cat_data["total_prices"])
            else:
                cat_data["price_range"]["min"] = 0
            
            cat_data["supplier_count"] = len(cat_data["supplier_count"])
            del cat_data["total_prices"]  # Удаляем временные данные
            
            result_categories.append(cat_data)
        
        # Сортируем по количеству товаров
        result_categories.sort(key=lambda x: x["product_count"], reverse=True)
        
        logger.info(f"Categories retrieved: {len(result_categories)} categories")
        
        return {
            "categories": result_categories,
            "total_categories": len(result_categories),
            "total_products": sum(cat["product_count"] for cat in result_categories)
        }
        
    except Exception as e:
        logger.error(f"Categories request failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get categories: {str(e)}")

@router.post("/procurement-recommendations",
            response_model=Dict[str, Any],
            summary="🛒 Рекомендации по закупкам", 
            description="Получение оптимальных рекомендаций по закупке товаров")
async def get_procurement_recommendations(
    request: Request,
    procurement_request: ProcurementRecommendationRequest,
    integration_adapter: LegacyIntegrationAdapter = Depends(get_integration_adapter)
) -> Dict[str, Any]:
    """
    Получение рекомендаций по оптимальной закупке товаров
    
    Анализирует требуемые товары и предлагает оптимальную стратегию закупки
    с учетом цен, надежности поставщиков и бюджетных ограничений
    
    Returns:
        Оптимальные рекомендации по закупкам
    """
    logger.info(f"Procurement recommendations requested for {len(procurement_request.required_products)} products")
    
    try:
        # Преобразуем запрос в формат для unified системы
        required_products = procurement_request.required_products
        
        # Получаем рекомендации через unified систему
        recommendations = integration_adapter.get_procurement_recommendations_report(required_products)
        
        # Адаптируем ответ под API формат
        result = {
            "total_products_requested": len(required_products),
            "budget_limit": procurement_request.budget_limit,
            "optimization_criteria": procurement_request.optimize_for,
            "recommendations": recommendations.get("catalog_data", {}),
            "cost_analysis": recommendations.get("analytics", {}),
            "supplier_recommendations": recommendations.get("additional_analysis", {}).get("supplier_recommendations", []),
            "total_estimated_cost": 0,  # Будет рассчитан
            "potential_savings": 0,     # Будет рассчитан
            "feasible_within_budget": True
        }
        
        # Рассчитываем общую стоимость
        catalog_products = result["recommendations"].get("products", [])
        total_cost = 0
        total_savings = 0
        
        for product in catalog_products:
            if isinstance(product, dict):
                total_cost += product.get("best_price", 0)
                total_savings += product.get("savings", 0)
        
        result["total_estimated_cost"] = total_cost
        result["potential_savings"] = total_savings
        
        # Проверяем бюджетные ограничения
        if procurement_request.budget_limit and total_cost > procurement_request.budget_limit:
            result["feasible_within_budget"] = False
            result["budget_overrun"] = total_cost - procurement_request.budget_limit
        
        logger.info(f"Procurement recommendations generated: total_cost={total_cost}, savings={total_savings}")
        
        return result
        
    except Exception as e:
        logger.error(f"Procurement recommendations failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate recommendations: {str(e)}") 