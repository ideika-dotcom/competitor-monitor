"""
Сервис для работы с ProxyAPI (OpenAI-совместимый API)
https://proxyapi.ru/docs/openai-text-generation
"""
import base64
import json
import re
import time
import logging
from typing import Optional

from openai import OpenAI

from backend.config import settings
from backend.models.schemas import CompetitorAnalysis, ImageAnalysis

# Логгер для сервиса
logger = logging.getLogger("competitor_monitor.openai")


class OpenAIService:
    """Сервис для анализа через OpenAI / ProxyAPI с поддержкой HTTP-прокси"""
    
    def __init__(self):
        logger.info("=" * 50)
        logger.info("Инициализация OpenAI сервиса")
        
        # Определяем, какой ключ и URL использовать
        # Если задан прямой OPENAI_API_KEY (начинается с sk-...), используем его напрямую к OpenAI
        # Иначе используем ProxyAPI
        if settings.openai_api_key and settings.openai_api_key.startswith("sk-") and not "your_" in settings.openai_api_key:
            api_key = settings.openai_api_key
            base_url = "https://api.openai.com/v1"
            logger.info("  Используется прямой доступ к OpenAI API")
        else:
            api_key = settings.proxy_api_key
            base_url = settings.proxy_api_base_url
            logger.info(f"  Используется ProxyAPI Base URL: {base_url}")
        
        logger.info(f"  Модель текста: {settings.openai_model}")
        logger.info(f"  Модель vision: {settings.openai_vision_model}")
        logger.info(f"  API ключ: {'*' * 10}...{api_key[-4:] if api_key else 'НЕ ЗАДАН'}")
        
        # Настройка HTTP клиента с поддержкой прокси, если задан PROXY_URL / PROXY
        http_client = None
        if settings.proxy_url:
            logger.info(f"  🌐 Настройка HTTP-прокси: {settings.proxy_url[:30]}...")
            import httpx
            http_client = httpx.Client(
                proxy=settings.proxy_url,
                timeout=60.0
            )
        
        # Создаем OpenAI клиент
        client_kwargs = {
            "api_key": api_key,
            "base_url": base_url
        }
        if http_client:
            client_kwargs["http_client"] = http_client
            
        self.client = OpenAI(**client_kwargs)
        self.model = settings.openai_model
        self.vision_model = settings.openai_vision_model
        
        logger.info("OpenAI сервис инициализирован успешно ✓")
        logger.info("=" * 50)
    
    def _parse_json_response(self, content: str) -> dict:
        """Извлечь JSON из ответа модели"""
        logger.debug(f"Парсинг JSON ответа, длина: {len(content)} символов")
        
        # Пробуем найти JSON в markdown блоке
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
        if json_match:
            content = json_match.group(1)
            logger.debug("JSON найден в markdown блоке")
        
        # Пробуем найти JSON объект
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            content = json_match.group(0)
            logger.debug("JSON объект извлечён")
        
        try:
            result = json.loads(content)
            logger.debug(f"JSON успешно распарсен, ключей: {len(result)}")
            return result
        except json.JSONDecodeError as e:
            logger.warning(f"Ошибка парсинга JSON: {e}")
            logger.debug(f"Проблемный контент: {content[:200]}...")
            return {}
    
    async def analyze_text(self, text: str) -> CompetitorAnalysis:
        """Анализ текста конкурента"""
        logger.info("=" * 50)
        logger.info("📝 АНАЛИЗ ТЕКСТА КОНКУРЕНТА")
        logger.info(f"  Длина текста: {len(text)} символов")
        logger.info(f"  Превью: {text[:100]}...")
        logger.info(f"  Модель: {self.model}")
        
        system_prompt = """Ты — сильный Python-разработчик, продуктовый инженер и эксперт по конкурентной разведке в строительной нише инъекционной гидроизоляции (фундаменты, подвалы, паркинги, бассейны, лифтовые шахты, бетонные конструкции и деформационные швы).

Проанализируй предоставленный текст конкурента и верни структурированный, чистый JSON-ответ без markdown блоков (без ```json ... ```) и лишнего текста вокруг.

Каждый список (массив) в JSON должен содержать строго 3-5 пунктов. Все оценки (score) должны быть целыми числами от 0 до 10.

Формат ответа (строго чистый JSON):
{
    "strengths": ["сильная сторона 1", "сильная сторона 2", "сильная сторона 3"],
    "weaknesses": ["слабая сторона 1", "слабая сторона 2", "слабая сторона 3"],
    "unique_offers": ["уникальное предложение 1", "уникальное предложение 2", "уникальное предложение 3"],
    "ad_hypotheses": ["рекламная гипотеза 1", "рекламная гипотеза 2", "рекламная гипотеза 3"],
    "recommendations": ["рекомендация по улучшению 1", "рекомендация по улучшению 2", "рекомендация по улучшению 3"],
    "design_score": 7,
    "animation_potential": 5,
    "conversion_potential": 6,
    "trust_score": 8,
    "summary": "Краткое резюме анализа текста конкурента в строительной нише инъекционной гидроизоляции"
}

Важные требования:
1. Пиши строго на русском языке.
2. Будь конкретен, профессионален и практичен, оперируй строительными терминами (пакеры, смолы, гели, микроцементы, гидроизоляция швов и т.д.).
3. Убедись, что оценки (design_score, animation_potential, conversion_potential, trust_score) — это целые числа от 0 до 10.
4. Каждый массив в ответе должен содержать строго от 3 до 5 содержательных пунктов.
5. Ответ должен быть СТРОГО чистым JSON. Не оборачивай в ```json, не пиши преамбулы и заключения. Ответ должен начинаться с { и заканчиваться на }."""

        start_time = time.time()
        logger.info("  Отправка запроса к API...")
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Проанализируй текст конкурента:\n\n{text}"}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            elapsed = time.time() - start_time
            logger.info(f"  ✓ Ответ получен за {elapsed:.2f} сек")
            
            content = response.choices[0].message.content
            logger.info(f"  Длина ответа: {len(content)} символов")
            logger.debug(f"  Использовано токенов: {response.usage.total_tokens if response.usage else 'N/A'}")
            
            data = self._parse_json_response(content)
            
            result = CompetitorAnalysis(
                strengths=data.get("strengths", []),
                weaknesses=data.get("weaknesses", []),
                unique_offers=data.get("unique_offers", []),
                ad_hypotheses=data.get("ad_hypotheses", []),
                recommendations=data.get("recommendations", []),
                design_score=int(data.get("design_score", 0)),
                animation_potential=int(data.get("animation_potential", 0)),
                conversion_potential=int(data.get("conversion_potential", 0)),
                trust_score=int(data.get("trust_score", 0)),
                summary=data.get("summary", "")
            )
            
            logger.info(f"  Результат: {len(result.strengths)} сильных, {len(result.weaknesses)} слабых сторон")
            logger.info("=" * 50)
            
            return result
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"  ✗ Ошибка API за {elapsed:.2f} сек: {e}")
            logger.error("=" * 50)
            raise
    
    async def analyze_image(self, image_base64: str, mime_type: str = "image/jpeg") -> ImageAnalysis:
        """Анализ изображения (баннер, сайт, фото объекта, схема инъектирования)"""
        logger.info("=" * 50)
        logger.info("🖼️ АНАЛИЗ ИЗОБРАЖЕНИЯ")
        logger.info(f"  Размер base64: {len(image_base64)} символов")
        logger.info(f"  MIME тип: {mime_type}")
        logger.info(f"  Модель: {self.vision_model}")
        
        system_prompt = """Ты — эксперт по визуальному маркетингу, продуктовому дизайну и конкурентной разведке в строительной нише инъекционной гидроизоляции (фундаменты, подвалы, паркинги, бассейны, лифтовые шахты, бетонные конструкции).

Проанализируй изображение конкурента (скриншот сайта, рекламный баннер, фото работ по инъектированию, схему узлов или материалов) и верни структурированный, чистый JSON-ответ без markdown разметки и лишнего текста вокруг.

Каждый список (массив) в ответе должен содержать строго 3-5 пунктов. Все оценки (score) должны быть целыми числами от 0 до 10.

Формат ответа (строго чистый JSON):
{
    "description": "Детальное описание того, что изображено на картинке с точки зрения строительной ниши и визуальной подачи",
    "marketing_insights": ["маркетинговый инсайт 1", "маркетинговый инсайт 2", "маркетинговый инсайт 3"],
    "visual_style_score": 7,
    "visual_style_analysis": "Подробный анализ визуального стиля, цветовой гаммы, шрифтов и профессионализма оформления",
    "ad_hypotheses": ["рекламная гипотеза 1", "рекламная гипотеза 2", "рекламная гипотеза 3"],
    "recommendations": ["рекомендация 1", "рекомендация 2", "рекомендация 3"],
    "design_score": 7,
    "animation_potential": 6,
    "conversion_potential": 7,
    "trust_score": 8
}

Важные требования:
1. Пиши строго на русском языке.
2. Оценки (visual_style_score, design_score, animation_potential, conversion_potential, trust_score) — целые числа от 0 до 10.
3. Каждый массив (marketing_insights, ad_hypotheses, recommendations) должен содержать строго 3-5 содержательных пунктов.
4. Фокусируйся на строительной нише инъекционной гидроизоляции и усиления конструкций.
5. Ответ должен быть СТРОГО чистым JSON без каких-либо ```json или вступительного текста. Ответ должен начинаться с { и заканчиваться на }."""

        start_time = time.time()
        logger.info("  Отправка запроса к Vision API...")
        
        try:
            response = self.client.chat.completions.create(
                model=self.vision_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Проанализируй это изображение конкурента в нише инъекционной гидроизоляции:"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                     "url": f"data:{mime_type};base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            elapsed = time.time() - start_time
            logger.info(f"  ✓ Ответ получен за {elapsed:.2f} сек")
            
            content = response.choices[0].message.content
            logger.info(f"  Длина ответа: {len(content)} символов")
            
            data = self._parse_json_response(content)
            
            result = ImageAnalysis(
                description=data.get("description", ""),
                marketing_insights=data.get("marketing_insights", []),
                visual_style_score=int(data.get("visual_style_score", data.get("design_score", 0))),
                visual_style_analysis=data.get("visual_style_analysis", ""),
                ad_hypotheses=data.get("ad_hypotheses", []),
                recommendations=data.get("recommendations", []),
                design_score=int(data.get("design_score", data.get("visual_style_score", 0))),
                animation_potential=int(data.get("animation_potential", 0)),
                conversion_potential=int(data.get("conversion_potential", 0)),
                trust_score=int(data.get("trust_score", 0))
            )
            
            logger.info(f"  Результат: дизайн {result.design_score}/10, доверие {result.trust_score}/10")
            logger.info(f"  Инсайтов: {len(result.marketing_insights)}, гипотез: {len(result.ad_hypotheses)}")
            logger.info("=" * 50)
            
            return result
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"  ✗ Ошибка Vision API за {elapsed:.2f} сек: {e}")
            logger.error("=" * 50)
            raise
    
    async def analyze_parsed_content(
        self, 
        title: Optional[str], 
        meta_description: Optional[str] = None,
        h1: Optional[str] = None, 
        body_text: Optional[str] = None
    ) -> CompetitorAnalysis:
        """Анализ распарсенного контента сайта в строительной нише инъекционной гидроизоляции"""
        logger.info("📄 Анализ распарсенного контента")
        logger.info(f"  Title: {title[:50] if title else 'N/A'}...")
        logger.info(f"  Meta Description: {meta_description[:50] if meta_description else 'N/A'}...")
        logger.info(f"  H1: {h1[:50] if h1 else 'N/A'}...")
        logger.info(f"  Body text: {body_text[:50] if body_text else 'N/A'}...")
        
        content_parts = []
        if title:
            content_parts.append(f"Заголовок страницы (title): {title}")
        if meta_description:
            content_parts.append(f"Meta описание (description): {meta_description}")
        if h1:
            content_parts.append(f"Главный заголовок (H1): {h1}")
        if body_text:
            content_parts.append(f"Основной текст страницы (innerText):\n{body_text[:15000]}")
        
        combined_text = "\n\n".join(content_parts)
        
        if not combined_text.strip():
            logger.warning("  ⚠ Контент пустой, возвращаем пустой анализ")
            return CompetitorAnalysis(
                summary="Не удалось извлечь контент для анализа"
            )
        
        return await self.analyze_text(combined_text)
    
    async def analyze_website_screenshot(
        self,
        screenshot_base64: str,
        url: str,
        title: Optional[str] = None,
        meta_description: Optional[str] = None,
        h1: Optional[str] = None,
        body_text: Optional[str] = None
    ) -> CompetitorAnalysis:
        """Комплексный анализ сайта конкурента по скриншоту и распарсенному тексту в нише инъекционной гидроизоляции"""
        logger.info("=" * 50)
        logger.info("🌐 КОМПЛЕКСНЫЙ АНАЛИЗ САЙТА")
        logger.info(f"  URL: {url}")
        logger.info(f"  Title: {title[:50] if title else 'N/A'}...")
        logger.info(f"  Meta Description: {meta_description[:50] if meta_description else 'N/A'}...")
        logger.info(f"  H1: {h1[:50] if h1 else 'N/A'}...")
        logger.info(f"  Размер скриншота: {len(screenshot_base64)} символов base64")
        logger.info(f"  Модель: {self.vision_model}")
        
        # Формируем контекст из извлечённых данных
        context_parts = [f"URL сайта конкурента: {url}"]
        if title:
            context_parts.append(f"Title: {title}")
        if meta_description:
            context_parts.append(f"Meta Description: {meta_description}")
        if h1:
            context_parts.append(f"Главный заголовок (H1): {h1}")
        if body_text:
            context_parts.append(f"Текстовое наполнение страницы:\n{body_text[:4000]}")
        
        context = "\n\n".join(context_parts)
        logger.debug(f"  Контекст:\n{context}")
        
        system_prompt = """Ты — сильный Python-разработчик и ведущий продуктовый эксперт по конкурентной разведке в нише инъекционной гидроизоляции (фундаменты, подвалы, паркинги, бассейны, лифтовые шахты, бетонные конструкции, деформационные швы).

Проанализируй сайт конкурента по скриншоту и тексту. Верни результат СТРОГО в виде чистого JSON без ```json и без лишнего текста.

Формат ответа (строго чистый JSON):
{
    "strengths": ["сильная сторона 1", "сильная сторона 2", "сильная сторона 3"],
    "weaknesses": ["слабая сторона 1", "слабая сторона 2", "слабая сторона 3"],
    "unique_offers": ["уникальное предложение 1", "уникальное предложение 2", "уникальное предложение 3"],
    "ad_hypotheses": ["рекламная гипотеза 1", "рекламная гипотеза 2", "рекламная гипотеза 3"],
    "recommendations": ["рекомендация 1", "рекомендация 2", "рекомендация 3"],
    "design_score": 8,
    "animation_potential": 6,
    "conversion_potential": 7,
    "trust_score": 8,
    "summary": "Комплексное резюме конкурентного анализа сайта в нише инъекционной гидроизоляции"
}

Требования:
- Оценки design_score, animation_potential, conversion_potential, trust_score — целые числа от 0 до 10.
- Каждый массив строго 3-5 пунктов на русском языке.
- Ответ СТРОГО чистый JSON."""

        start_time = time.time()
        logger.info("  Отправка скриншота в Vision API...")
        
        try:
            response = self.client.chat.completions.create(
                model=self.vision_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"Проведи комплексный анализ сайта гидроизоляции:\n\n{context}"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{screenshot_base64}"
                                }
                            }
                        ]
                    }
                ],
                temperature=0.7,
                max_tokens=3000
            )
            
            elapsed = time.time() - start_time
            logger.info(f"  ✓ Ответ получен за {elapsed:.2f} сек")
            
            content = response.choices[0].message.content
            logger.info(f"  Длина ответа: {len(content)} символов")
            
            data = self._parse_json_response(content)
            
            result = CompetitorAnalysis(
                strengths=data.get("strengths", []),
                weaknesses=data.get("weaknesses", []),
                unique_offers=data.get("unique_offers", []),
                ad_hypotheses=data.get("ad_hypotheses", []),
                recommendations=data.get("recommendations", []),
                design_score=int(data.get("design_score", 0)),
                animation_potential=int(data.get("animation_potential", 0)),
                conversion_potential=int(data.get("conversion_potential", 0)),
                trust_score=int(data.get("trust_score", 0)),
                summary=data.get("summary", "")
            )
            
            logger.info(f"  Результат: сильных={len(result.strengths)}, гипотез={len(result.ad_hypotheses)}")
            logger.info(f"  Резюме: {result.summary[:100]}...")
            logger.info("=" * 50)
            
            return result
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"  ✗ Ошибка Vision API за {elapsed:.2f} сек: {e}")
            logger.error("=" * 50)
            raise


# Глобальный экземпляр
logger.info("Создание глобального экземпляра OpenAI сервиса...")
openai_service = OpenAIService()

