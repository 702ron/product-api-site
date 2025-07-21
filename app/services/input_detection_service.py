"""
Input detection service for identifying product lookup input types.
Supports ASIN, FNSKU, and GTIN/UPC detection with validation.
"""
import re
import logging
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class InputType(str, Enum):
    """Supported input types for product lookup."""
    ASIN = "asin"
    FNSKU = "fnsku"
    GTIN_UPC = "gtin_upc"


class InputDetectionResult(BaseModel):
    """Result of input type detection."""
    input_type: InputType
    input_value: str
    confidence: float = 1.0
    detected_format: str
    credit_cost: int
    validation_errors: Optional[List[str]] = None


class InputDetectionService:
    """Service for detecting and validating product lookup input types."""
    
    # Credit costs for different input types
    CREDIT_COSTS = {
        InputType.ASIN: 1,
        InputType.FNSKU: 10,
        InputType.GTIN_UPC: 1
    }
    
    # Input patterns for detection
    PATTERNS = {
        # ASIN patterns: B followed by 9 alphanumeric, OR 10 digits
        InputType.ASIN: [
            r'^B[0-9A-Z]{9}$',  # Standard B + 9 alphanumeric
            r'^[0-9]{10}$'       # 10-digit numeric ASIN
        ],
        # FNSKU: 10 alphanumeric characters, NOT starting with B
        InputType.FNSKU: [
            r'^[A-Z0-9]{10}$'   # 10 alphanumeric (will exclude B-prefix with logic)
        ],
        # GTIN/UPC patterns: 8, 12, 13, or 14 digits
        InputType.GTIN_UPC: [
            r'^[0-9]{8}$',      # UPC-E (8 digits)
            r'^[0-9]{12}$',     # UPC-A (12 digits)
            r'^[0-9]{13}$',     # EAN-13 (13 digits)
            r'^[0-9]{14}$'      # GTIN-14 (14 digits)
        ]
    }
    
    def __init__(self):
        """Initialize the input detection service."""
        pass
    
    def detect_input_type(self, input_value: str) -> InputDetectionResult:
        """
        Detect the input type based on format patterns.
        
        Args:
            input_value: The input string to analyze
            
        Returns:
            InputDetectionResult with detected type and metadata
            
        Raises:
            ValueError: If input format is not recognized
        """
        if not input_value or not input_value.strip():
            raise ValueError("Input value cannot be empty")
        
        cleaned_input = input_value.strip().upper()
        logger.info(f"Detecting input type for: {cleaned_input}")
        
        # Check ASIN patterns first (most specific)
        for pattern in self.PATTERNS[InputType.ASIN]:
            if re.match(pattern, cleaned_input):
                return self._create_detection_result(
                    InputType.ASIN, 
                    cleaned_input, 
                    pattern,
                    confidence=1.0
                )
        
        # Check FNSKU (10 alphanumeric NOT starting with B)
        if re.match(self.PATTERNS[InputType.FNSKU][0], cleaned_input) and not cleaned_input.startswith('B'):
            # Additional validation for FNSKU format
            validation_errors = self._validate_fnsku(cleaned_input)
            return self._create_detection_result(
                InputType.FNSKU,
                cleaned_input,
                self.PATTERNS[InputType.FNSKU][0],
                confidence=0.95,  # Slightly lower confidence due to format overlap
                validation_errors=validation_errors
            )
        
        # Check GTIN/UPC patterns
        for pattern in self.PATTERNS[InputType.GTIN_UPC]:
            if re.match(pattern, cleaned_input):
                validation_errors = self._validate_gtin_upc(cleaned_input)
                return self._create_detection_result(
                    InputType.GTIN_UPC,
                    cleaned_input,
                    pattern,
                    confidence=1.0,
                    validation_errors=validation_errors
                )
        
        # If no patterns match, raise error with helpful message
        raise ValueError(
            f"Unrecognized input format: '{input_value}'. "
            f"Expected: ASIN (B123456789 or 1234567890), "
            f"FNSKU (ABC1234567), or GTIN/UPC (8-14 digits)"
        )
    
    def _create_detection_result(
        self, 
        input_type: InputType, 
        input_value: str, 
        pattern: str,
        confidence: float = 1.0,
        validation_errors: Optional[List[str]] = None
    ) -> InputDetectionResult:
        """Create a standardized detection result."""
        return InputDetectionResult(
            input_type=input_type,
            input_value=input_value,
            confidence=confidence,
            detected_format=pattern,
            credit_cost=self.CREDIT_COSTS[input_type],
            validation_errors=validation_errors
        )
    
    def _validate_fnsku(self, fnsku: str) -> Optional[List[str]]:
        """
        Validate FNSKU format and characteristics.
        
        Args:
            fnsku: The FNSKU string to validate
            
        Returns:
            List of validation errors, or None if valid
        """
        errors = []
        
        # Basic length check (already done by regex, but double-check)
        if len(fnsku) != 10:
            errors.append(f"FNSKU must be exactly 10 characters, got {len(fnsku)}")
        
        # Check for invalid characters
        if not fnsku.isalnum():
            errors.append("FNSKU must contain only letters and numbers")
        
        # Check that it doesn't start with B (would be ASIN)
        if fnsku.startswith('B'):
            errors.append("FNSKU cannot start with 'B' (that would be an ASIN)")
        
        # Common FNSKU characteristics validation
        if fnsku.isdigit():
            errors.append("FNSKU should not be all numbers (might be GTIN/UPC)")
        
        return errors if errors else None
    
    def _validate_gtin_upc(self, code: str) -> Optional[List[str]]:
        """
        Validate GTIN/UPC format and checksum.
        
        Args:
            code: The GTIN/UPC string to validate
            
        Returns:
            List of validation errors, or None if valid
        """
        errors = []
        
        # Basic numeric check
        if not code.isdigit():
            errors.append("GTIN/UPC must contain only digits")
            return errors
        
        # Validate checksum for common formats
        if len(code) in [8, 12, 13, 14]:
            if not self._validate_gtin_checksum(code):
                errors.append("Invalid GTIN/UPC checksum")
        
        return errors if errors else None
    
    def _validate_gtin_checksum(self, code: str) -> bool:
        """
        Validate GTIN checksum using the standard algorithm.
        
        Args:
            code: The GTIN code to validate
            
        Returns:
            True if checksum is valid, False otherwise
        """
        try:
            # GTIN checksum algorithm
            digits = [int(d) for d in code[:-1]]  # All but last digit
            check_digit = int(code[-1])
            
            # Calculate checksum (alternating weights of 3 and 1 from right to left)
            total = 0
            for i, digit in enumerate(reversed(digits)):
                weight = 3 if i % 2 == 0 else 1
                total += digit * weight
            
            calculated_check = (10 - (total % 10)) % 10
            return calculated_check == check_digit
            
        except (ValueError, IndexError):
            return False
    
    def get_credit_cost(self, input_type: InputType) -> int:
        """
        Get the credit cost for a specific input type.
        
        Args:
            input_type: The input type to get cost for
            
        Returns:
            Credit cost as integer
        """
        return self.CREDIT_COSTS[input_type]
    
    def get_all_patterns(self) -> Dict[str, List[str]]:
        """
        Get all detection patterns for documentation/testing.
        
        Returns:
            Dictionary mapping input types to their regex patterns
        """
        return {input_type.value: patterns for input_type, patterns in self.PATTERNS.items()}
    
    def validate_manual_override(self, input_value: str, manual_type: InputType) -> InputDetectionResult:
        """
        Validate a manual input type override.
        
        Args:
            input_value: The input string
            manual_type: The manually specified input type
            
        Returns:
            InputDetectionResult with validation
            
        Raises:
            ValueError: If manual override conflicts with input format
        """
        cleaned_input = input_value.strip().upper()
        
        # Check if manual type matches any pattern for that type
        patterns = self.PATTERNS[manual_type]
        for pattern in patterns:
            if re.match(pattern, cleaned_input):
                # Additional validation based on type
                validation_errors = None
                if manual_type == InputType.FNSKU:
                    if cleaned_input.startswith('B'):
                        validation_errors = ["Manual FNSKU override conflicts with ASIN format (starts with B)"]
                    else:
                        validation_errors = self._validate_fnsku(cleaned_input)
                elif manual_type == InputType.GTIN_UPC:
                    validation_errors = self._validate_gtin_upc(cleaned_input)
                
                return self._create_detection_result(
                    manual_type,
                    cleaned_input,
                    pattern,
                    confidence=0.8,  # Lower confidence for manual override
                    validation_errors=validation_errors
                )
        
        # Manual override doesn't match expected pattern
        raise ValueError(
            f"Manual override '{manual_type.value}' doesn't match input format '{input_value}'"
        )


# Create global instance for easy import
input_detector = InputDetectionService()