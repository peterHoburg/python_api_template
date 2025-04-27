# Plan for TICKET-005A: Define base Pydantic models

## Overview
This ticket involves creating base Pydantic models with common validation logic that will be used throughout the application. These base models will provide consistent validation and behavior for all schemas.

## Current State
- The project uses Pydantic in a few places:
  - `src/pat/schemas/error.py` defines error response schemas
  - `src/pat/api/responses.py` defines API response models
  - `src/pat/config.py` uses Pydantic for configuration
- There are no base Pydantic models for general use
- The `schemas` directory contains a misplaced SQLAlchemy model in `schemas.py`

## Goals
1. Create base Pydantic models that provide common functionality
2. Implement common validation methods
3. Set up configuration for all models
4. Ensure proper organization of the schemas directory

## Implementation Plan
1. Create a new file `src/pat/schemas/base.py` to define base Pydantic models
2. Implement the following base models:
   - `BaseSchema`: A base model with common configuration and methods
   - `BaseCreateSchema`: For create operations
   - `BaseUpdateSchema`: For update operations
   - `BaseResponseSchema`: For API responses
3. Add common validation methods to these base models
4. Set up proper configuration for all models
5. Fix the organization of the schemas directory (move SQLAlchemy model to models directory)
6. Write tests for the base models

## Technical Considerations
- Use Pydantic v2 features where appropriate
- Ensure models are compatible with FastAPI
- Follow functional programming principles where possible
- Implement proper type hints
- Add comprehensive docstrings
- Ensure all validation methods are reusable