import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

    # Azure OpenAI
    AZURE_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    AZURE_OPENAI_API_KEY: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    AZURE_OPENAI_API_VERSION: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-06-01")
    AZURE_OPENAI_DEPLOYMENT: str = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5.4")

    # MySQL
    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "127.0.0.1")
    MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_USER: str = os.getenv("MYSQL_USER", "reports_user")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "reports_pass")
    MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "reports_db")

    # Team members: "telegram_id:username,telegram_id:username"
    TEAM_MEMBERS_RAW: str = os.getenv("TEAM_MEMBERS", "")



    # Owner ID
    OWNER_ID_RAW: str = os.getenv("OWNER_ID", "")

    @property
    def OWNER_ID(self) -> int | None:
        if self.OWNER_ID_RAW.strip() and self.OWNER_ID_RAW.strip().isdigit():
            return int(self.OWNER_ID_RAW.strip())
        return None

    # Timezone
    TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Almaty")

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
        )

    @property
    def team_members(self) -> dict[int, str]:
        """Returns {telegram_id: username} dict."""
        if not self.TEAM_MEMBERS_RAW.strip():
            return {}
        members = {}
        for pair in self.TEAM_MEMBERS_RAW.split(","):
            pair = pair.strip()
            if ":" in pair:
                tid, uname = pair.split(":", 1)
                members[int(tid.strip())] = uname.strip()
        return members

    TELEGRAM_API_URL: str = "https://api.telegram.org"

    @property
    def bot_api_url(self) -> str:
        return f"{self.TELEGRAM_API_URL}/bot{self.TELEGRAM_BOT_TOKEN}"


settings = Settings()
