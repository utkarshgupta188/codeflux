import logging
from app.services.agent.agent_service import AgentService
from app.models.repo import ReadmeResponse

logger = logging.getLogger("readme_service")

class ReadmeService:
    @staticmethod
    async def generate(repo_id: str) -> ReadmeResponse:
        """
        Uses the AI Agent to generate a README for the specified repository.
        """
        prompt = (
            "Analyze the codebase and generate a comprehensive, professional README.md. "
            "Include sections for: Project Overview, Key Features, Installation, Usage, and Technologies Used. "
            "Make it visually appealing with proper Markdown formatting."
        )
        
        logger.info(f"Generating README for repo: {repo_id}")
        
        result = await AgentService.run(prompt, repo_id=repo_id)
        
        return ReadmeResponse(
            repoId=repo_id,
            content=result.final_answer
        )
