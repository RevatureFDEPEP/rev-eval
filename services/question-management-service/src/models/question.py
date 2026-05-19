from beanie import Document, Indexed
from pydantic import BaseModel, Field, field_validator
from enum import Enum
from typing import List, Optional, Union
from datetime import datetime, timezone


class QuestionType(str, Enum):
    """Enumeration of supported question types."""
    MCQ = "mcq"
    MULTI = "multi"
    TRUE_FALSE = "true_false"
    TEXT = "text"


class OptionCreate(BaseModel):
    """
    Schema for creating an option (used in request body).

    The option_id is auto-generated based on the position in the list.
    Users only need to provide the text.
    """
    text: str = Field(..., min_length=1, max_length=500, description="Option text")

    @field_validator('text')
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Validate and sanitize option text."""
        v = v.strip()
        if not v:
            raise ValueError("Option text cannot be empty")
        return v


class Option(BaseModel):
    """
    Stored option model for MCQ and MULTI questions.

    Attributes:
        option_id: Auto-generated identifier based on position (1-indexed)
        text: Display text for the option
    """
    option_id: int = Field(..., ge=1, description="Auto-generated option identifier (1-indexed)")
    text: str = Field(..., min_length=1, max_length=500, description="Option text")

    @field_validator('text')
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Validate and sanitize option text."""
        v = v.strip()
        if not v:
            raise ValueError("Option text cannot be empty")
        return v


class Question(Document):
    """
    Question document model for MongoDB using Beanie ODM.

    This model stores questions of various types with appropriate validation
    and constraints based on the question type. Inherits from Beanie's Document
    class for MongoDB operations.

    Uses MongoDB's auto-generated _id as the primary identifier.

    MongoDB Collection: questions
    """
    type: QuestionType
    question_text: str = Field(..., min_length=10, max_length=2000)
    options: Optional[List[Option]] = None
    correct_answers: Optional[List[Union[int, bool, str]]] = None
    sample_answer: Optional[str] = Field(None, max_length=5000)
    answer_explanation: Optional[str] = Field(None, max_length=2000)
    difficulty: Optional[str] = Field(default="medium", pattern="^(easy|medium|hard)$")
    skills: List[str] = Field(default_factory=list, max_length=20)
    tags: List[str] = Field(default_factory=list, max_length=30)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator('question_text')
    @classmethod
    def validate_question_text(cls, v: str) -> str:
        """Validate and sanitize question text."""
        v = v.strip()
        if len(v) < 10:
            raise ValueError("question_text must be at least 10 characters long")
        return v

    class Settings:
        """Beanie document settings."""
        name = "questions"  # MongoDB collection name
        use_enum_values = True  # Store enum values instead of enum names
        validate_on_save = True  # Validate before saving to database

    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
                "type": "mcq",
                "question_text": "What is the capital of France?",
                "options": [
                    {"option_id": 1, "text": "London"},
                    {"option_id": 2, "text": "Paris"},
                    {"option_id": 3, "text": "Berlin"},
                    {"option_id": 4, "text": "Madrid"}
                ],
                "correct_answers": [2],
                "answer_explanation": "Paris is the capital and most populous city of France.",
                "difficulty": "easy",
                "skills": ["Geography", "General Knowledge"],
                "tags": ["europe", "capitals"]
            }
        }