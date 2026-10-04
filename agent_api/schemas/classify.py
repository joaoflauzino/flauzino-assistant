from pydantic import BaseModel, Field


class ClassifyItemInput(BaseModel):
    id: str
    merchant: str
    raw_title: str
    raw_description: str | None = None
    direction: str  # "IN", "OUT"
    amount: float


class CategoryOption(BaseModel):
    key: str
    display_name: str


class ClassifyBatchRequest(BaseModel):
    transactions: list[ClassifyItemInput] = Field(..., max_length=60)
    expense_categories: list[CategoryOption] = Field(default_factory=list)
    income_categories: list[CategoryOption] = Field(default_factory=list)


class ClassifySuggestion(BaseModel):
    id: str
    category: str | None = None
    confidence: float | None = None


class ClassifyBatchResponse(BaseModel):
    suggestions: list[ClassifySuggestion]


# Modelos para Structured Output do LangChain / LLM
class LLMItemClassification(BaseModel):
    id: str = Field(description="O mesmo ID fornecido na transação de entrada")
    category: str | None = Field(
        default=None,
        description="A chave exata da categoria sugerida (deve pertencer à lista fornecida), ou null se não houver certeza ou for nome de pessoa física sem contexto comercial.",
    )
    confidence: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Nível de confiança na classificação de 0.0 a 1.0",
    )


class LLMBatchClassificationResult(BaseModel):
    items: list[LLMItemClassification] = Field(default_factory=list)
