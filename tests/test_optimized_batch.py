#!/usr/bin/env python3
"""
Тест оптимизированного пакетного режима BatchChatGPTProcessor
"""

import os
import sys
import asyncio
import time
from dotenv import load_dotenv

# Настройка путей
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from modules.batch_chatgpt_processor import BatchChatGPTProcessor
from modules.universal_excel_parser import UniversalExcelParser

def create_test_products(count: int = 50):
    """Создание тестовых данных для проверки пакетного режима"""
    test_products = [
        {'original_name': 'Молоко коровье 3.2% жирности пастеризованное', 'price': 89.50, 'unit': 'л'},
        {'original_name': 'Хлеб пшеничный белый формовой', 'price': 45.00, 'unit': 'шт'},
        {'original_name': 'Мясо говядина высший сорт охлажденное', 'price': 750.00, 'unit': 'кг'},
        {'original_name': 'Рыба семга свежая филе', 'price': 1200.00, 'unit': 'кг'},
        {'original_name': 'Картофель молодой мытый', 'price': 25.00, 'unit': 'кг'},
        {'original_name': 'Апельсины импортные сладкие', 'price': 120.00, 'unit': 'кг'},
        {'original_name': 'Масло подсолнечное рафинированное дезодорированное', 'price': 95.00, 'unit': 'л'},
        {'original_name': 'Сыр российский твердый 45%', 'price': 380.00, 'unit': 'кг'},
        {'original_name': 'Яйца куриные столовые C1', 'price': 85.00, 'unit': 'десяток'},
        {'original_name': 'Крупа гречневая ядрица высший сорт', 'price': 110.00, 'unit': 'кг'},
        {'original_name': 'Сахар-песок белый ГОСТ', 'price': 55.00, 'unit': 'кг'},
        {'original_name': 'Чай черный байховый листовой', 'price': 250.00, 'unit': 'пачка'},
        {'original_name': 'Кофе натуральный растворимый сублимированный', 'price': 890.00, 'unit': 'банка'},
        {'original_name': 'Макароны спагетти твердые сорта пшеницы', 'price': 75.00, 'unit': 'пачка'},
        {'original_name': 'Рис длиннозерный шлифованный премиум', 'price': 120.00, 'unit': 'кг'},
        {'original_name': 'Соль поваренная пищевая йодированная', 'price': 15.00, 'unit': 'пачка'},
        {'original_name': 'Перец черный молотый острый', 'price': 180.00, 'unit': 'пачка'},
        {'original_name': 'Лук репчатый желтый свежий', 'price': 30.00, 'unit': 'кг'},
        {'original_name': 'Морковь столовая мытая', 'price': 35.00, 'unit': 'кг'},
        {'original_name': 'Капуста белокочанная свежая', 'price': 20.00, 'unit': 'кг'},
        {'original_name': 'Томаты красные свежие парниковые', 'price': 180.00, 'unit': 'кг'},
        {'original_name': 'Огурцы свежие тепличные длинноплодные', 'price': 120.00, 'unit': 'кг'},
        {'original_name': 'Бананы желтые спелые импортные', 'price': 95.00, 'unit': 'кг'},
        {'original_name': 'Яблоки красные сладкие отечественные', 'price': 80.00, 'unit': 'кг'},
        {'original_name': 'Творог обезжиренный 0% пастообразный', 'price': 140.00, 'unit': 'пачка'},
        {'original_name': 'Сметана 20% жирности пастеризованная', 'price': 120.00, 'unit': 'банка'},
        {'original_name': 'Йогурт натуральный без добавок', 'price': 65.00, 'unit': 'стакан'},
        {'original_name': 'Масло сливочное крестьянское 72.5%', 'price': 180.00, 'unit': 'пачка'},
        {'original_name': 'Колбаса вареная докторская ГОСТ', 'price': 320.00, 'unit': 'кг'},
        {'original_name': 'Сосиски молочные высший сорт', 'price': 280.00, 'unit': 'кг'},
        {'original_name': 'Курица целая охлажденная 1 категория', 'price': 160.00, 'unit': 'кг'},
        {'original_name': 'Свинина корейка без кости охлажденная', 'price': 420.00, 'unit': 'кг'},
        {'original_name': 'Фарш говяжий свежемороженый', 'price': 380.00, 'unit': 'кг'},
        {'original_name': 'Печенье овсяное с изюмом сладкое', 'price': 150.00, 'unit': 'пачка'},
        {'original_name': 'Конфеты шоколадные ассорти премиум', 'price': 450.00, 'unit': 'коробка'},
        {'original_name': 'Вода питьевая негазированная очищенная', 'price': 25.00, 'unit': 'бутылка'},
        {'original_name': 'Сок яблочный натуральный 100%', 'price': 85.00, 'unit': 'пакет'},
        {'original_name': 'Лимонад газированный цитрусовый', 'price': 45.00, 'unit': 'бутылка'},
        {'original_name': 'Пиво светлое фильтрованное 4.5%', 'price': 120.00, 'unit': 'бутылка'},
        {'original_name': 'Вино красное сухое столовое', 'price': 380.00, 'unit': 'бутылка'},
        {'original_name': 'Моющее средство для посуды концентрат', 'price': 85.00, 'unit': 'бутылка'},
        {'original_name': 'Стиральный порошок автомат универсальный', 'price': 320.00, 'unit': 'пачка'},
        {'original_name': 'Туалетная бумага 2-слойная белая', 'price': 180.00, 'unit': 'упаковка'},
        {'original_name': 'Шампунь для всех типов волос', 'price': 250.00, 'unit': 'бутылка'},
        {'original_name': 'Зубная паста комплексная защита', 'price': 120.00, 'unit': 'тюбик'},
        {'original_name': 'Крем для рук увлажняющий', 'price': 180.00, 'unit': 'тюбик'},
        {'original_name': 'Мыло туалетное антибактериальное', 'price': 45.00, 'unit': 'кусок'},
        {'original_name': 'Дезодорант спрей длительная защита', 'price': 220.00, 'unit': 'баллон'},
        {'original_name': 'Прокладки женские ультратонкие', 'price': 180.00, 'unit': 'упаковка'},
        {'original_name': 'Подгузники детские размер 3', 'price': 890.00, 'unit': 'упаковка'}
    ]
    
    # Дублируем данные если нужно больше товаров
    result = []
    for i in range(count):
        product = test_products[i % len(test_products)].copy()
        if i >= len(test_products):
            product['original_name'] = f"{product['original_name']} #{i+1}"
        result.append(product)
    
    return result

async def test_batch_processing():
    """Тестирование оптимизированного пакетного режима"""
    print("🚀 ТЕСТ ОПТИМИЗИРОВАННОГО ПАКЕТНОГО РЕЖИМА")
    print("=" * 60)
    
    # Проверяем наличие API ключа
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY не установлен")
        return
    
    # Создаем процессор
    processor = BatchChatGPTProcessor(api_key)
    
    # Тестовые сценарии
    test_cases = [
        {'name': 'Малый пакет', 'count': 15},
        {'name': 'Средний пакет', 'count': 30}, 
        {'name': 'Большой пакет', 'count': 50}
    ]
    
    for test_case in test_cases:
        print(f"\n📦 ТЕСТ: {test_case['name']} ({test_case['count']} товаров)")
        print("-" * 40)
        
        # Создаем тестовые данные
        products = create_test_products(test_case['count'])
        
        # Показываем настройки
        optimal_batch_size = processor.optimize_batch_size(products)
        batches = processor.split_products_into_batches(products, optimal_batch_size)
        
        print(f"📊 Товаров: {len(products)}")
        print(f"🔧 Оптимальный размер пакета: {optimal_batch_size}")
        print(f"📦 Количество пакетов: {len(batches)}")
        
        # Запуск обработки
        start_time = time.time()
        
        try:
            result = await processor.process_all_products(products, "Тестовый поставщик")
            
            processing_time = time.time() - start_time
            
            if 'error' in result:
                print(f"❌ Ошибка: {result['error']}")
                continue
            
            # Анализируем результаты
            stats = result.get('processing_stats', {})
            processed_products = result.get('products', [])
            
            print(f"⏱️ Время обработки: {processing_time:.2f}с")
            print(f"✅ Обработано товаров: {len(processed_products)}/{len(products)}")
            print(f"📈 Успешность: {stats.get('success_rate', 0):.1%}")
            print(f"🔥 Успешных пакетов: {stats.get('successful_batches', 0)}/{stats.get('total_batches', 0)}")
            print(f"🪙 Приблизительно токенов: {stats.get('estimated_tokens', 0)}")
            
            # Показываем примеры обработанных товаров
            print(f"\n🎯 ПРИМЕРЫ ОБРАБОТАННЫХ ТОВАРОВ:")
            for i, product in enumerate(processed_products[:3]):
                print(f"{i+1}. {product.get('original_name', 'N/A')[:50]}...")
                print(f"   → {product.get('standardized_name', 'N/A')}")
                print(f"   🏷️ Бренд: {product.get('brand', 'N/A')}")
                print(f"   📦 Размер: {product.get('size', 'N/A')} {product.get('unit', 'N/A')}")
                print(f"   🏪 Категория: {product.get('category', 'N/A')}")
                print(f"   💰 Цена: {product.get('price', 0)} {product.get('currency', 'IDR')}")
                print()
            
            # Расчет эффективности
            products_per_second = len(processed_products) / processing_time if processing_time > 0 else 0
            tokens_per_second = stats.get('estimated_tokens', 0) / processing_time if processing_time > 0 else 0
            
            print(f"⚡ ПРОИЗВОДИТЕЛЬНОСТЬ:")
            print(f"   📦 Товаров/сек: {products_per_second:.1f}")
            print(f"   🪙 Токенов/сек: {tokens_per_second:.1f}")
            
        except Exception as e:
            processing_time = time.time() - start_time
            print(f"❌ Ошибка теста: {e}")
            print(f"⏱️ Время до ошибки: {processing_time:.2f}с")

def main():
    """Главная функция"""
    asyncio.run(test_batch_processing())

if __name__ == "__main__":
    main()