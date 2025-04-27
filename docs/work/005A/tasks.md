# Tasks for TICKET-005A: Define base Pydantic models

## Task List

1. [x] Run initial `make lint` and `make test` to ensure everything passes before starting
2. [x] Create a new file `src/pat/schemas/base.py` for base Pydantic models
   - [x] Import necessary modules
   - [x] Add comprehensive docstring for the module
3. [x] Implement `BaseSchema` class
   - [x] Define common configuration for all models
   - [x] Add docstring explaining the purpose and usage
   - [x] Implement common utility methods
4. [x] Implement `BaseCreateSchema` class
   - [x] Inherit from `BaseSchema`
   - [x] Add specific configuration for create operations
   - [x] Add docstring explaining the purpose and usage
5. [x] Implement `BaseUpdateSchema` class
   - [x] Inherit from `BaseSchema`
   - [x] Configure all fields as optional for partial updates
   - [x] Add docstring explaining the purpose and usage
6. [x] Implement `BaseResponseSchema` class
   - [x] Inherit from `BaseSchema`
   - [x] Add specific configuration for response models
   - [x] Add docstring explaining the purpose and usage
7. [x] Implement common validation methods
   - [x] Add email validation method
   - [x] Add string normalization method
   - [ ] Add date/time validation methods
   - [x] Add any other common validation methods
8. [x] Fix organization of schemas directory
   - [x] Move SQLAlchemy model from `schemas.py` to appropriate location in models directory
   - [x] Update imports in any files that reference the moved model
9. [x] Create tests for base models
   - [x] Create test file `tests/src/test_pat/test_schemas_base.py`
   - [x] Write tests for `BaseSchema`
   - [x] Write tests for `BaseCreateSchema`
   - [x] Write tests for `BaseUpdateSchema`
   - [x] Write tests for `BaseResponseSchema`
   - [x] Write tests for validation methods
10. [x] Run `make lint` and `make test` to ensure everything passes
11. [x] Update `docs/tickets.md` to mark the ticket as done
