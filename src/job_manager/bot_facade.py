from typing import Any, Dict

from config.logger_config import logger


class BotState:
    """BotFacade state class"""

    def __init__(self):
        logger.info("Initializing BotState class")
        self.reset()

    def reset(self):
        logger.info("Resetting BotState class state")
        self.parameters_set = False
        self.search_parameters_set = False
        self.resume_set = False
        self.answerer_and_agent_set = False

    def validate_state(self, required_keys):
        logger.info(f"Checking BotState flags: {required_keys}")
        for key in required_keys:
            if not getattr(self, key):
                logger.error(f"State flag check failed, flag {key} not set")
                raise ValueError(f"Flag {key.replace('_', ' ').capitalize()} must be set")
        logger.info("State check passed successfully")


class BotFacade:
    """Bot interface class"""

    def __init__(
        self,
        resume_component: Any,
        search_component: Any,
        apply_component: Any,
        llm_agent_component: Any,
    ):
        logger.info("Initializing BotFacade class")
        self.resume_component = resume_component  # ResumeScraper
        self.search_component = search_component  # SearchCustomizer
        self.apply_component = apply_component  # JobApplier
        self.llm_agent_component = llm_agent_component  # ApplyAgent
        self.state = BotState()
        self.resume = None
        self.parameters = None
        self.llm_answerer_component = None
        self.llm_agent_component = None

    def set_parameters(self, parameters: Dict[str, Any]) -> None:
        """Check that all parameters are set correctly"""
        logger.info("Setting parameters")
        self._validate_non_empty(parameters, "Parameters")
        self.parameters = parameters
        self.apply_component.set_parameters(parameters)
        self.state.parameters_set = True
        logger.info("All parameters set successfully")

    async def set_search_parameters(self, parameters: Dict[str, Any]) -> None:
        """Set search parameters (async)"""
        logger.info("Setting search parameters")
        self._validate_non_empty(parameters, "Parameters")
        self.search_component.set_advanced_search_params(parameters)
        await self.search_component.set_search_params()
        self.state.search_parameters_set = True
        logger.info("Search parameters successfully set")

    def set_answerer_and_agent(
        self,
        llm_answerer_component: Any,
        llm_agent_component: Any,
        parameters: Dict[str, Any],
    ) -> None:
        """Start class for working with LLM and resume handler"""
        logger.info("Starting class for working with LLM and resume handler")
        self._ensure_search_parameters_set()
        self.llm_answerer_component = llm_answerer_component
        self.llm_agent_component = llm_agent_component
        self.llm_answerer_component.set_search_parameters(parameters)
        self.apply_component.set_answerer_and_agent(llm_answerer_component, llm_agent_component)
        self.state.answerer_and_agent_set = True
        logger.info("LLM class successfully started")

    def set_resume(
        self, resume_structured: Dict[str, Any], resume_text: str, resume_text_anonymized: str
    ) -> None:
        """Collect resume information from site"""
        logger.info("Collecting resume information")
        self._ensure_answerer_and_agent_set()
        self.resume = resume_structured
        self.apply_component.set_resume(resume_structured)
        self.llm_answerer_component.set_resume(resume_structured, resume_text_anonymized)
        self.llm_agent_component.set_resume(resume_text)
        self.state.resume_set = True
        logger.info("Resume information successfully collected")

    def set_resume_generator(self, resume_generator_manager) -> None:
        """Start class for creating resume"""
        logger.info("Starting class for working with LLM and resume handler")
        self._ensure_resume_set()
        self.apply_component.set_resume_generator_manager(resume_generator_manager)
        logger.info("Resume manager successfully started")

    def set_pause_checker(self, pause_checker) -> None:
        """Set pause checker function for pausing execution"""
        logger.info("Setting pause checker function")
        self.apply_component.set_pause_checker(pause_checker)
        logger.info("Pause checker successfully set")

    async def start_apply(self) -> None:
        """Start resume sending process (async)"""
        self.state.validate_state(
            ["resume_set", "parameters_set", "search_parameters_set", "answerer_and_agent_set"]
        )
        logger.info("Starting job search process")
        await self.apply_component.start_applying()
        logger.info("Job search process successfully completed")

    def _validate_non_empty(self, value, name) -> None:
        """Check that field with name `name` is not empty"""
        logger.debug(f"Checking that field with name {name} is not empty")
        if not value:
            logger.error(f"Check failed: field with name {name} is empty")
            raise ValueError(f"{name} cannot be empty.")
        logger.debug(f"Check of field with name {name} completed successfully")

    def _ensure_search_parameters_set(self) -> None:
        """Check that search parameters are set"""
        logger.debug("Checking that search parameters are set")
        if not self.state.search_parameters_set:
            logger.error("Search parameters not set")
            raise ValueError("Search parameters must be set for correct operation.")
        logger.debug("Search parameters are set")

    def _ensure_resume_set(self) -> None:
        """Check that resume is set"""
        logger.debug("Checking that resume is set")
        if not self.state.resume_set:
            logger.error("Resume not set")
            raise ValueError("Resume must be set for correct operation.")
        logger.debug("Resume is set")

    def _ensure_answerer_and_agent_set(self) -> None:
        """Check that answerer and agent are set"""
        logger.debug("Checking that resume is set")
        if not self.state.answerer_and_agent_set:
            logger.error("Answerer and agent not set")
            raise ValueError("Answerer and agent must be set for correct operation.")
        logger.debug("Resume is set")
