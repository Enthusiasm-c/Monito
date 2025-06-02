#!/usr/bin/env python3
"""
Создание тестового PDF файла с прайс-листом для тестирования парсера
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
import os

def create_test_pdf():
    """Создание тестового PDF файла с таблицей товаров"""
    filename = "data/temp/test_price_list.pdf"
    
    # Убеждаемся, что директория существует
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    # Создаем документ
    doc = SimpleDocTemplate(filename, pagesize=A4)
    elements = []
    
    # Стили
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    
    # Заголовок
    title = Paragraph("ПРАЙС-ЛИСТ ПРОДУКТОВ", title_style)
    elements.append(title)
    elements.append(Spacer(1, 20))
    
    # Подзаголовок
    subtitle = Paragraph("ООО 'Тестовый Поставщик'", styles['Heading2'])
    elements.append(subtitle)
    elements.append(Spacer(1, 20))
    
    # Данные таблицы
    data = [
        ['№', 'Наименование товара', 'Цена (руб)', 'Единица', 'Категория'],
        ['1', 'Молоко коровье пастеризованное 3.2%', '89.50', 'л', 'Молочные продукты'],
        ['2', 'Хлеб пшеничный белый', '45.00', 'шт', 'Хлебобулочные изделия'],
        ['3', 'Мясо говядина высший сорт', '750.00', 'кг', 'Мясные продукты'],
        ['4', 'Рыба семга свежая', '1200.00', 'кг', 'Рыбные продукты'],
        ['5', 'Картофель молодой', '25.00', 'кг', 'Овощи'],
        ['6', 'Апельсины импортные', '120.00', 'кг', 'Фрукты'],
        ['7', 'Масло подсолнечное рафинированное', '95.00', 'л', 'Масложировые продукты'],
        ['8', 'Сыр российский твердый', '380.00', 'кг', 'Молочные продукты'],
        ['9', 'Куриные яйца C1', '85.00', 'десяток', 'Яичные продукты'],
        ['10', 'Гречка ядрица', '110.00', 'кг', 'Крупы'],
        ['11', 'Сахар-песок белый', '55.00', 'кг', 'Сахар'],
        ['12', 'Чай черный байховый', '250.00', 'пачка', 'Чай и кофе']
    ]
    
    # Создаем таблицу
    table = Table(data, colWidths=[0.8*inch, 3*inch, 1.2*inch, 1*inch, 2*inch])
    
    # Стиль таблицы
    table.setStyle(TableStyle([
        # Заголовок
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        
        # Данные
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        
        # Границы
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        # Выравнивание цен по правому краю
        ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Номера по центру
    ]))
    
    elements.append(table)
    
    # Добавляем информацию о поставщике
    elements.append(Spacer(1, 30))
    info = Paragraph("<b>Контактная информация:</b><br/>Тел: +7 (999) 123-45-67<br/>Email: test@supplier.ru", styles['Normal'])
    elements.append(info)
    
    # Генерируем PDF
    doc.build(elements)
    
    print(f"✅ Тестовый PDF создан: {filename}")
    return filename

if __name__ == "__main__":
    try:
        # Попробуем импортировать reportlab
        import reportlab
        create_test_pdf()
    except ImportError:
        print("❌ Для создания PDF нужно установить reportlab:")
        print("pip install reportlab")
        
        # Создаем простой текстовый файл как fallback
        print("📝 Создаю текстовую версию...")
        content = """ПРАЙС-ЛИСТ ПРОДУКТОВ
ООО 'Тестовый Поставщик'

№    Наименование товара                      Цена (руб)  Единица      Категория
1    Молоко коровье пастеризованное 3.2%     89.50       л            Молочные продукты
2    Хлеб пшеничный белый                    45.00       шт           Хлебобулочные изделия
3    Мясо говядина высший сорт               750.00      кг           Мясные продукты
4    Рыба семга свежая                       1200.00     кг           Рыбные продукты
5    Картофель молодой                       25.00       кг           Овощи
"""
        
        os.makedirs("data/temp", exist_ok=True)
        with open("data/temp/test_price_list.txt", "w", encoding="utf-8") as f:
            f.write(content)
        
        print("✅ Создан текстовый файл: data/temp/test_price_list.txt")