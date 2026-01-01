from typing import Dict, Any

class GenieMCP:
    """
    Optional MCP. Enabled ONLY on Databricks.
    """
    def __init__(self, enabled: bool = False):
        self.enabled = enabled

    def can_handle(self, intent: str) -> bool:
        # Keep this strict
        return intent in {"AGGREGATION", "SIMPLE_LOOKUP"}

    def execute(self, question: str) -> Dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("Genie MCP disabled")

        # ---- DBX ONLY ----
        # response = genie_client.query(question)
        # return {
        #   "sql": response.sql,
        #   "df": response.dataframe
        # }

        raise NotImplementedError("Genie only available on Databricks")
