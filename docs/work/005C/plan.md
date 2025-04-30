# Plan for TICKET-005C: Add custom validators

## Overview
This ticket involves implementing custom validators for complex validation logic in the application. The goal is to create reusable validators for common patterns, implement complex validation rules, and add clear error messages for validation failures.

## Current State
The application currently has basic validation functionality:
- Automatic string stripping for all string fields via a field validator in `BaseSchema`
- Email validation and normalization via the `validate_email` function
- String normalization via the `normalize_string` function

## Implementation Plan

1. Create a new module `src/pat/schemas/validators.py` to house all custom validators
   - This will keep the validators organized and separate from the base schema definitions
   - Makes it easier to import and reuse validators across different schemas

2. Implement common validators for:
   - Phone numbers (with international format support)
   - URLs (with validation for different protocols and formats)
   - Dates and date ranges (with validation for logical constraints)
   - Numeric ranges (with min/max validation and custom error messages)
   - Alphanumeric strings (with pattern validation)
   - Enum values (with case-insensitive matching)

3. Implement complex validation rules:
   - Conditional validation (field required only if another field has a specific value)
   - Cross-field validation (comparing values between multiple fields)
   - Collection validation (validating items in lists or dictionaries)
   - Dependent field validation (ensuring related fields are consistent)

4. Add comprehensive error messages:
   - Create a consistent error message format
   - Include field name, validation rule, and expected format in error messages
   - Support internationalization for error messages

5. Update the base schema classes to use the new validators:
   - Add methods to `BaseSchema` for common validation patterns
   - Update documentation to reflect new validation capabilities

6. Create comprehensive tests for all validators:
   - Test valid and invalid inputs
   - Test edge cases
   - Test error messages

## Expected Outcome
A set of reusable custom validators that handle complex validation scenarios, with clear error messages that help users understand validation failures.