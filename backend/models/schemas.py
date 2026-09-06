"""
Pydantic схемы для API
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# === Запросы ===

class TextAnalysisRequest(BaseModel):
    """Запрос на анализ текста"""
    text: str = Field(..., min_length=10, description="Текст для анализа")


class ParseDemoRequest(BaseModel):
    """Запрос на парсинг URL"""
    url: str = Field(..., description="URL для парсинга")


# === Ответы ===

class CompetitorAnalysis(BaseModel):
    """Структурированный анализ конкурента (Инъекционная гидроизоляция)"""
    strengths: List[str] = Field(default_factory=list, description="Сильные стороны")
    weaknesses: List[str] = Field(default_factory=list, description="Слабые стороны")
    unique_offers: List[str] = Field(default_factory=list, description="Уникальные предложения")
    ad_hypotheses: List[str] = Field(default_factory=list, description="Рекламные гипотезы")
    recommendations: List[str] = Field(default_factory=list, description="Рекомендации")
    design_score: int = Field(0, ge=0, le=10, description="Оценка дизайна (0-10)")
    animation_potential: int = Field(0, ge=0, le=10, description="Потенциал анимации (0-10)")
    conversion_potential: int = Field(0, ge=0, le=10, description="Потенциал конверсии (0-10)")
    trust_score: int = Field(0, ge=0, le=10, description="Уровень доверия (0-10)")
    summary: str = Field("", description="Общее резюме")


class ImageAnalysis(BaseModel):
    """Анализ изображения"""
    description: str = Field("", description="Описание изображения")
    marketing_insights: List[str] = Field(default_factory=list, description="Маркетинговые инсайты")
    visual_style_score: int = Field(0, ge=0, le=10, description="Оценка визуального стиля (0-10)")
    visual_style_analysis: str = Field("", description="Анализ визуального стиля")
    ad_hypotheses: List[str] = Field(default_factory=list, description="Рекламные гипотезы")
    recommendations: List[str] = Field(default_factory=list, description="Рекомендации")
    design_score: int = Field(0, ge=0, le=10, description="Оценка дизайна (0-10)")
    animation_potential: int = Field(0, ge=0, le=10, description="Потенциал анимации (0-10)")
    conversion_potential: int = Field(0, ge=0, le=10, description="Потенциал конверсии (0-10)")
    trust_score: int = Field(0, ge=0, le=10, description="Уровень доверия (0-10)")



class ParsedContent(BaseModel):
    """Результат парсинга страницы"""
    url: str
    title: Optional[str] = None
    meta_description: Optional[str] = None
    h1: Optional[str] = None
    body_text: Optional[str] = None
    first_paragraph: Optional[str] = None
    analysis: Optional[CompetitorAnalysis] = None
    error: Optional[str] = None


class TextAnalysisResponse(BaseModel):
    """Ответ на анализ текста"""
    success: bool
    analysis: Optional[CompetitorAnalysis] = None
    error: Optional[str] = None


class ImageAnalysisResponse(BaseModel):
    """Ответ на анализ изображения"""
    success: bool
    analysis: Optional[ImageAnalysis] = None
    error: Optional[str] = None


class ParseDemoResponse(BaseModel):
    """Ответ на парсинг"""
    success: bool
    data: Optional[ParsedContent] = None
    error: Optional[str] = None


# === История ===

class HistoryItem(BaseModel):
    """Элемент истории"""
    id: str
    timestamp: datetime
    request_type: str  # "text", "image", "parse"
    request_summary: str
    response_summary: str


class HistoryResponse(BaseModel):
    """Ответ со списком истории"""
    items: List[HistoryItem]
    total: int

