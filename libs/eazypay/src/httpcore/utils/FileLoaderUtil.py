
from typing import Any
from pydantic import BaseModel
import json
from httpcore.utils.log import logger

class FileLoaderUtil(BaseModel):

    @staticmethod
    def load_file_as_stream(file_name: str) -> Any:
        try:
            # assuming filename is sent with file path
            return open(file_name, 'rb').read()
        except FileNotFoundError:
            logger.error("An error occurred while loading the config")
            raise FileNotFoundError(f"File not found: {file_name}")

    @staticmethod
    def read_file_content_as_string(file_name: str) -> str:
        """
        Read file content as a string.
        """
        try:
            with FileLoaderUtil.load_file_as_stream(file_name) as file_stream:
                result = []
                for line in file_stream:
                    result.append(line.decode('utf-8') + '\n')
                return ''.join(result)
        except FileNotFoundError as e:
            logger.error(str(e))
            raise

    @staticmethod
    def read_file_content_as_json(file_name: str) -> Any:
        """
        Read file content and parse it as JSON.
        """
        try:
            with FileLoaderUtil.load_file_as_stream(file_name) as file_stream:
                file_content = file_stream.read().decode('utf-8')
                return json.loads(file_content)
        except FileNotFoundError as e:
            logger.error(str(e))
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON: {str(e)}")
            raise
