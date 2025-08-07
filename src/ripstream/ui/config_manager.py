# Copyright (c) 2025 ripstream and contributors. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.

"""Configuration manager for handling application configuration."""

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ripstream.config.user import UserConfig

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages application configuration loading, saving, and validation."""

    def __init__(self, config_path: Path | None = None):
        self.config_path = config_path or self._get_default_config_path()
        self.config: UserConfig | None = None

    def _get_default_config_path(self) -> Path:
        """Get the default configuration file path."""
        return Path.home() / ".config" / "ripstream" / "config.json"

    def load_config(self) -> UserConfig:
        """Load configuration from file or create default."""
        try:
            if self.config_path.exists():
                self.config = UserConfig.from_json_file(self.config_path)
                logger.info("Configuration loaded from %s", self.config_path)
            else:
                self.config = UserConfig()
                self._ensure_config_directory()
                self.save_config()
                logger.info("Default configuration created at %s", self.config_path)

        except (ValidationError, json.JSONDecodeError) as e:
            logger.warning("Invalid configuration file, creating default: %s", e)
            self.config = UserConfig()
            self._ensure_config_directory()
            self.save_config()

        except Exception:
            logger.exception("Failed to load configuration")
            self.config = UserConfig()

        return self.config

    def save_config(self) -> None:
        """Save current configuration to file."""
        if not self.config:
            logger.warning("No configuration to save")
            return

        try:
            self._ensure_config_directory()
            self.config.to_json_file(self.config_path)
            logger.info("Configuration saved to %s", self.config_path)

        except Exception:
            logger.exception("Failed to save configuration")

    def _ensure_config_directory(self) -> None:
        """Ensure the configuration directory exists."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

    def get_config(self) -> UserConfig:
        """Get the current configuration."""
        if not self.config:
            self.load_config()
        return self.config

    def update_config(self, new_config: UserConfig) -> None:
        """Update the configuration and save it."""
        self.config = new_config
        self.save_config()

    def get_service_config(self, service_name: str) -> Any:
        """Get configuration for a specific service."""
        config = self.get_config()
        return config.get_service_config(service_name)

    def validate_config(self) -> bool:
        """Validate the current configuration."""
        try:
            if self.config:
                # This will raise ValidationError if invalid
                UserConfig.model_validate(self.config.model_dump())
            else:
                return True
        except ValidationError:
            logger.exception("Configuration validation failed")
            return False
        else:
            return True
