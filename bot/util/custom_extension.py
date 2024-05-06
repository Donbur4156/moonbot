from interactions import Extension, Client
from logging import Logger
from configs import Configs
from util import DcLog, SQL
from whistle import EventDispatcher

class CustomExt(Extension):
    def __init__(self, client: Client, **kwargs) -> None:
        self._client = client
        self._config: Configs = kwargs.get("config")
        self._logger: Logger = kwargs.get("logger")
        self._dispatcher: EventDispatcher = kwargs.get("dispatcher")
        self._dclog: DcLog = kwargs.get("dc_log")
        self._sql: SQL = kwargs.get("sql")
        self.add_extension_postrun(self._dclog.cmd_log)
