import logging
from app.services.agent.agent_service import AgentService
from app.models.repo import ReadmeResponse

logger = logging.getLogger("readme_service")

class ReadmeService:
    @staticmethod
    async def generate(repo_id: str) -> ReadmeResponse:
        """
        Uses the AI Agent to generate a high-quality, professional README for the specified repository.
        """
        prompt = (
            "Analyze the codebase comprehensively and generate a STUNNING, PROFESSIONAL, and PRODUCTION-READY README.md. "
            "\n\nFOLLOW THESE CORE REQUIREMENTS:"
            "\n1. **Visual Appeal**: Use professional badges from shields.io (e.g., version, license, tech stack). Use emojis tastefully to improve scannability."
            "\n2. **Clear Structure**: Include the following sections:"
            "\n   - 🚀 **Overview**: A compelling hook explaining the project's value proposition."
            "\n   - ✨ **Key Features**: A bulleted list of the most important functionalities."
            "\n   - 🛠️ **Tech Stack**: A structured list of major libraries and frameworks used."
            "\n   - ⚙️ **Installation**: Precise, copy-pasteable commands for setup."
            "\n   - 📂 **Project Structure**: A brief overview of the directory layout."
            "\n   - 📖 **Usage**: Clear examples or commands to run/use the project."
            "\n   - 🤝 **Contributing**: Brief guidelines for contributors."
            "\n   - ⚖️ **License**: Mention the project license."
            "\n3. **Technical Depth**: If the codebase has complex architecture, include a simple Mermaid diagram or describe the data flow clearly."
            "\n4. **Formatting**: Use proper Markdown hierarchy (H1 for title, H2 for sections). Use tables for feature comparisons or compatibility if relevant."
            "\n\nYour response MUST BE only the Markdown content for the README. Do not include any meta-talk."
        )
        
        logger.info(f"Generating enhanced professional README for repo: {repo_id}")
        
        result = await AgentService.run(prompt, repo_id=repo_id)
        
        # In case the agent iterates and includes a thought or JSON wrapper in final_answer (though prompt discourages it)
        # we try to extract if it looks wrapped, though usually final_answer is clean.
        content = result.final_answer
        
        return ReadmeResponse(
            repoId=repo_id,
            content=content
        )
