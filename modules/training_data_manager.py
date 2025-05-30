#!/usr/bin/env python3
"""
Менеджер эталонных данных для обучения и сравнения результатов
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import pandas as pd

logger = logging.getLogger(__name__)

class TrainingDataManager:
    """Управление эталонными данными для обучения системы"""
    
    def __init__(self, training_dir: str = "training_data"):
        self.training_dir = Path(training_dir)
        self.training_dir.mkdir(exist_ok=True)
        
        # Структура папок
        self.original_files_dir = self.training_dir / "original_files"
        self.reference_data_dir = self.training_dir / "reference_data" 
        self.comparison_results_dir = self.training_dir / "comparison_results"
        
        for dir_path in [self.original_files_dir, self.reference_data_dir, self.comparison_results_dir]:
            dir_path.mkdir(exist_ok=True)
    
    def save_training_example(self, 
                            original_file_path: str, 
                            reference_data: Dict[str, Any],
                            example_name: str) -> str:
        """Сохранение эталонного примера"""
        try:
            # Копируем оригинальный файл
            import shutil
            original_file = Path(original_file_path)
            if original_file.exists():
                target_file = self.original_files_dir / f"{example_name}{original_file.suffix}"
                shutil.copy2(original_file_path, target_file)
                logger.info(f"Сохранен оригинальный файл: {target_file}")
            
            # Сохраняем эталонные данные
            reference_file = self.reference_data_dir / f"{example_name}_reference.json"
            with open(reference_file, 'w', encoding='utf-8') as f:
                json.dump(reference_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Сохранены эталонные данные: {reference_file}")
            return str(reference_file)
            
        except Exception as e:
            logger.error(f"Ошибка сохранения эталонного примера: {e}")
            return ""
    
    def load_reference_data(self, example_name: str) -> Optional[Dict[str, Any]]:
        """Загрузка эталонных данных"""
        try:
            reference_file = self.reference_data_dir / f"{example_name}_reference.json"
            if reference_file.exists():
                with open(reference_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return None
        except Exception as e:
            logger.error(f"Ошибка загрузки эталонных данных: {e}")
            return None
    
    def compare_results(self, 
                       actual_result: Dict[str, Any], 
                       reference_data: Dict[str, Any],
                       example_name: str) -> Dict[str, Any]:
        """Сравнение результатов с эталоном"""
        comparison = {
            "example_name": example_name,
            "timestamp": datetime.now().isoformat(),
            "supplier_comparison": self._compare_supplier_data(
                actual_result.get('supplier', {}),
                reference_data.get('supplier', {})
            ),
            "products_comparison": self._compare_products_data(
                actual_result.get('products', []),
                reference_data.get('products', [])
            ),
            "overall_metrics": {}
        }
        
        # Общие метрики
        comparison["overall_metrics"] = self._calculate_overall_metrics(comparison)
        
        # Сохраняем результат сравнения
        self._save_comparison_result(comparison, example_name)
        
        return comparison
    
    def _compare_supplier_data(self, actual: Dict, reference: Dict) -> Dict:
        """Сравнение данных поставщика"""
        fields = ['name', 'phone', 'email', 'address']
        comparison = {}
        
        for field in fields:
            actual_val = actual.get(field, '').strip().lower()
            reference_val = reference.get(field, '').strip().lower()
            
            if reference_val:  # Только если есть эталонное значение
                if actual_val == reference_val:
                    match_score = 1.0
                elif actual_val in reference_val or reference_val in actual_val:
                    match_score = 0.7
                else:
                    match_score = 0.0
            else:
                match_score = 1.0 if not actual_val else 0.5  # Нет эталона
            
            comparison[field] = {
                "actual": actual.get(field, ''),
                "reference": reference.get(field, ''),
                "match_score": match_score
            }
        
        return comparison
    
    def _compare_products_data(self, actual: List[Dict], reference: List[Dict]) -> Dict:
        """Сравнение товаров"""
        comparison = {
            "total_actual": len(actual),
            "total_reference": len(reference),
            "matched_products": [],
            "missing_products": [],
            "extra_products": [],
            "field_accuracy": {}
        }
        
        # Сопоставление товаров по названию
        matched_pairs = []
        unmatched_actual = actual.copy()
        unmatched_reference = reference.copy()
        
        for ref_product in reference:
            best_match = None
            best_score = 0
            
            for act_product in unmatched_actual:
                score = self._calculate_name_similarity(
                    act_product.get('original_name', ''),
                    ref_product.get('original_name', '')
                )
                if score > best_score and score > 0.7:  # Порог схожести
                    best_score = score
                    best_match = act_product
            
            if best_match:
                matched_pairs.append((best_match, ref_product))
                unmatched_actual.remove(best_match)
                unmatched_reference.remove(ref_product)
        
        # Анализ совпадений
        field_scores = {
            'brand': [], 'standardized_name': [], 'size': [], 
            'price': [], 'unit': [], 'category': []
        }
        
        for actual_prod, ref_prod in matched_pairs:
            product_comparison = {}
            
            for field in field_scores.keys():
                actual_val = str(actual_prod.get(field, '')).strip().lower()
                ref_val = str(ref_prod.get(field, '')).strip().lower()
                
                if field == 'price':
                    # Для цены проверяем численное совпадение
                    try:
                        actual_price = float(actual_prod.get('price', 0))
                        ref_price = float(ref_prod.get('price', 0))
                        
                        if ref_price > 0:
                            diff = abs(actual_price - ref_price) / ref_price
                            score = max(0, 1 - diff) if diff <= 1 else 0
                        else:
                            score = 1.0 if actual_price == 0 else 0.5
                    except:
                        score = 0.0
                else:
                    # Для текстовых полей
                    if ref_val:
                        if actual_val == ref_val:
                            score = 1.0
                        elif actual_val in ref_val or ref_val in actual_val:
                            score = 0.7
                        else:
                            score = 0.0
                    else:
                        score = 1.0 if not actual_val else 0.5
                
                field_scores[field].append(score)
                product_comparison[field] = {
                    "actual": actual_prod.get(field, ''),
                    "reference": ref_prod.get(field, ''),
                    "score": score
                }
            
            comparison["matched_products"].append({
                "actual_name": actual_prod.get('original_name', ''),
                "reference_name": ref_prod.get('original_name', ''),
                "field_comparison": product_comparison
            })
        
        # Средние оценки по полям
        for field, scores in field_scores.items():
            comparison["field_accuracy"][field] = {
                "average_score": sum(scores) / len(scores) if scores else 0,
                "total_comparisons": len(scores)
            }
        
        # Недостающие и лишние товары
        comparison["missing_products"] = [
            p.get('original_name', '') for p in unmatched_reference
        ]
        comparison["extra_products"] = [
            p.get('original_name', '') for p in unmatched_actual
        ]
        
        return comparison
    
    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Простое вычисление схожести названий"""
        name1 = name1.lower().strip()
        name2 = name2.lower().strip()
        
        if name1 == name2:
            return 1.0
        
        # Проверка вхождения
        if name1 in name2 or name2 in name1:
            return 0.8
        
        # Проверка общих слов
        words1 = set(name1.split())
        words2 = set(name2.split())
        
        if words1 and words2:
            intersection = len(words1 & words2)
            union = len(words1 | words2)
            return intersection / union
        
        return 0.0
    
    def _calculate_overall_metrics(self, comparison: Dict) -> Dict:
        """Расчет общих метрик качества"""
        supplier_scores = [
            data["match_score"] for data in comparison["supplier_comparison"].values()
        ]
        
        products_comp = comparison["products_comparison"]
        field_scores = [
            data["average_score"] for data in products_comp["field_accuracy"].values()
        ]
        
        total_ref_products = products_comp["total_reference"]
        matched_count = len(products_comp["matched_products"])
        
        return {
            "supplier_accuracy": sum(supplier_scores) / len(supplier_scores) if supplier_scores else 0,
            "products_field_accuracy": sum(field_scores) / len(field_scores) if field_scores else 0,
            "products_detection_rate": matched_count / total_ref_products if total_ref_products > 0 else 0,
            "overall_score": 0  # Будет рассчитан ниже
        }
    
    def _save_comparison_result(self, comparison: Dict, example_name: str):
        """Сохранение результата сравнения"""
        try:
            result_file = self.comparison_results_dir / f"{example_name}_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(comparison, f, indent=2, ensure_ascii=False)
            logger.info(f"Сохранен результат сравнения: {result_file}")
        except Exception as e:
            logger.error(f"Ошибка сохранения результата сравнения: {e}")
    
    def create_reference_template(self) -> Dict[str, Any]:
        """Создание шаблона для эталонных данных"""
        return {
            "supplier": {
                "name": "Название компании",
                "phone": "+62 xxx xxxx",
                "whatsapp": "+62 xxx xxxx", 
                "email": "email@company.com",
                "address": "Адрес компании"
            },
            "products": [
                {
                    "original_name": "Точное название из документа",
                    "brand": "БРЕНД",
                    "standardized_name": "Стандартизированное название на английском",
                    "size": "размер",
                    "unit": "единица измерения",
                    "price": 0,
                    "currency": "IDR",
                    "category": "категория",
                    "confidence": 0.95
                }
            ],
            "metadata": {
                "document_type": "price_list",
                "language": "indonesian/english",
                "total_pages": 1,
                "notes": "Дополнительные заметки"
            }
        }
    
    def get_training_examples_list(self) -> List[str]:
        """Получение списка доступных эталонных примеров"""
        examples = []
        for file_path in self.reference_data_dir.glob("*_reference.json"):
            example_name = file_path.stem.replace("_reference", "")
            examples.append(example_name)
        return sorted(examples)
    
    def generate_training_report(self) -> Dict[str, Any]:
        """Генерация отчета по всем эталонным данным"""
        examples = self.get_training_examples_list()
        
        report = {
            "total_examples": len(examples),
            "examples": examples,
            "summary": {
                "avg_supplier_accuracy": 0,
                "avg_products_accuracy": 0,
                "common_issues": []
            }
        }
        
        # Анализ последних результатов сравнений
        comparison_files = list(self.comparison_results_dir.glob("*.json"))
        
        if comparison_files:
            supplier_accuracies = []
            product_accuracies = []
            
            for comp_file in comparison_files[-10:]:  # Последние 10 результатов
                try:
                    with open(comp_file, 'r', encoding='utf-8') as f:
                        comp_data = json.load(f)
                    
                    metrics = comp_data.get('overall_metrics', {})
                    supplier_accuracies.append(metrics.get('supplier_accuracy', 0))
                    product_accuracies.append(metrics.get('products_field_accuracy', 0))
                except:
                    continue
            
            if supplier_accuracies:
                report["summary"]["avg_supplier_accuracy"] = sum(supplier_accuracies) / len(supplier_accuracies)
            if product_accuracies:
                report["summary"]["avg_products_accuracy"] = sum(product_accuracies) / len(product_accuracies)
        
        return report