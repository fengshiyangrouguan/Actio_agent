from pydantic import BaseModel, Field
from typing import Optional, List

# [system]
class SystemConfig(BaseModel):
    version: str = "0.0.0"
    owner_id: Optional[int] = None
    log_level: str = "INFO"

# [persona]
class PersonaConfig(BaseModel):
    bot_name: str = ""
    bot_personality: str

# Main Config
class BotConfig(BaseModel):
    system: SystemConfig = Field(...)
    persona: PersonaConfig = Field(...)