from typing import List, Optional
from src.models.question import Question
from beanie.operators import In
from beanie import PydanticObjectId


class QuestionRepository:
    """
    Repository layer for Question data access using Beanie ODM.

    This class handles all database operations for questions using Beanie's
    Document methods, providing a clean interface between the service layer
    and MongoDB.
    """

    @staticmethod
    async def create(question: Question) -> str:
        """
        Create a new question in the database using Beanie.

        Args:
            question: Question document instance

        Returns:
            str: The MongoDB _id of the inserted document

        Raises:
            ValueError: If validation fails
        """
        await question.insert()
        return str(question.id)

    @staticmethod
    async def get_all(limit: int = 100, skip: int = 0) -> List[Question]:
        """
        Retrieve all questions from the database with pagination.

        Args:
            limit: Maximum number of questions to return (default: 100)
            skip: Number of questions to skip (default: 0)

        Returns:
            List[Question]: List of Question documents
        """
        questions = await Question.find_all().skip(skip).limit(limit).to_list()
        return questions

    @staticmethod
    async def get_by_id(qid: str) -> Optional[Question]:
        """
        Retrieve a question by its MongoDB _id using Beanie.

        Args:
            qid: The MongoDB ObjectId as string

        Returns:
            Optional[Question]: The Question document if found, None otherwise
        """
        try:
            return await Question.get(PydanticObjectId(qid))
        except Exception:
            return None

    @staticmethod
    async def update(qid: str, data: dict) -> bool:
        """
        Update a question with the provided data using Beanie.

        Args:
            qid: The MongoDB ObjectId as string
            data: Dictionary of fields to update

        Returns:
            bool: True if a document was modified, False otherwise
        """
        try:
            question = await Question.get(PydanticObjectId(qid))
            if not question:
                return False

            # Update fields from data dictionary
            for key, value in data.items():
                if hasattr(question, key):
                    setattr(question, key, value)

            await question.save()
            return True
        except Exception:
            return False

    @staticmethod
    async def delete(qid: str) -> bool:
        """
        Delete a question by its MongoDB _id using Beanie.

        Args:
            qid: The MongoDB ObjectId as string

        Returns:
            bool: True if a document was deleted, False otherwise
        """
        try:
            question = await Question.get(PydanticObjectId(qid))
            if not question:
                return False

            await question.delete()
            return True
        except Exception:
            return False

    @staticmethod
    async def count(filter_dict: dict = None) -> int:
        """
        Count questions matching the filter.

        Args:
            filter_dict: Dictionary filter (default: None for all documents)

        Returns:
            int: Number of matching documents
        """
        if filter_dict is None or len(filter_dict) == 0:
            return await Question.count()

        # For simple filters, use Beanie's query
        # This is a basic implementation - can be enhanced for complex queries
        return await Question.find(filter_dict).count()

    @staticmethod
    async def find_by_type(question_type: str, limit: int = 100) -> List[Question]:
        """
        Find questions by type using Beanie.

        Args:
            question_type: The type of questions to find (mcq, multi, true_false, text)
            limit: Maximum number of questions to return

        Returns:
            List[Question]: List of matching Question documents
        """
        return await Question.find(Question.type == question_type).limit(limit).to_list()

    @staticmethod
    async def find_by_skill(skill: str, limit: int = 100) -> List[Question]:
        """
        Find questions by skill using Beanie.

        Args:
            skill: The skill to search for
            limit: Maximum number of questions to return

        Returns:
            List[Question]: List of matching Question documents
        """
        return await Question.find(In(Question.skills, [skill])).limit(limit).to_list()

    @staticmethod
    async def find_by_difficulty(difficulty: str, limit: int = 100) -> List[Question]:
        """
        Find questions by difficulty level.

        Args:
            difficulty: The difficulty level (easy, medium, hard)
            limit: Maximum number of questions to return

        Returns:
            List[Question]: List of matching Question documents
        """
        return await Question.find(Question.difficulty == difficulty).limit(limit).to_list()

    @staticmethod
    async def find_by_tags(tags: List[str], limit: int = 100) -> List[Question]:
        """
        Find questions that have any of the specified tags.

        Args:
            tags: List of tags to search for
            limit: Maximum number of questions to return

        Returns:
            List[Question]: List of matching Question documents
        """
        return await Question.find(In(Question.tags, tags)).limit(limit).to_list()
