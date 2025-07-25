# backend/utils/env_validator.py
import os
import sys
from typing import List, Dict, Any
import structlog

logger = structlog.get_logger()


class EnvironmentValidator:
    """Validate required environment variables and setup"""

    REQUIRED_ENV_VARS = [
        "GOOGLE_CLOUD_PROJECT",
        "JWT_SECRET_KEY",
        "FI_MCP_BASE_URL",
        "FI_MCP_API_KEY"
    ]

    OPTIONAL_ENV_VARS = [
        "VERTEX_AI_LOCATION",
        "FIRESTORE_DATABASE",
        "ENVIRONMENT",
        "DEBUG"
    ]

    @classmethod
    def validate_environment(cls) -> Dict[str, Any]:
        """Validate all environment requirements"""

        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "env_vars": {}
        }

        # Check required variables
        for var in cls.REQUIRED_ENV_VARS:
            value = os.getenv(var)
            if not value:
                validation_result["errors"].append(f"Missing required environment variable: {var}")
                validation_result["valid"] = False
            else:
                validation_result["env_vars"][var] = "✓ Set"

        # Check optional variables
        for var in cls.OPTIONAL_ENV_VARS:
            value = os.getenv(var)
            if not value:
                validation_result["warnings"].append(f"Optional environment variable not set: {var}")
            else:
                validation_result["env_vars"][var] = "✓ Set"

        # Check Google Cloud credentials
        gcp_creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not gcp_creds:
            validation_result["warnings"].append("GOOGLE_APPLICATION_CREDENTIALS not set - using default credentials")
        elif not os.path.exists(gcp_creds):
            validation_result["errors"].append(f"Google Cloud credentials file not found: {gcp_creds}")
            validation_result["valid"] = False
        else:
            validation_result["env_vars"]["GOOGLE_APPLICATION_CREDENTIALS"] = "✓ Set"

        # Log results
        if validation_result["valid"]:
            logger.info("✅ Environment validation passed",
                        vars_count=len(validation_result["env_vars"]))
        else:
            logger.error("❌ Environment validation failed",
                         errors=validation_result["errors"])

        if validation_result["warnings"]:
            logger.warning("⚠️ Environment warnings",
                           warnings=validation_result["warnings"])

        return validation_result

    @classmethod
    def exit_if_invalid(cls):
        """Exit application if environment is invalid"""
        result = cls.validate_environment()

        if not result["valid"]:
            print("❌ Environment validation failed:")
            for error in result["errors"]:
                print(f"  • {error}")
            print("\nPlease fix the above errors and restart the application.")
            sys.exit(1)

        return result
