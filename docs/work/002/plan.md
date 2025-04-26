# Plan for TICKET-002: Set up SQLAlchemy with async support

## Current State
- Basic async SQLAlchemy engine is set up in `src/pat/utils/db.py`
- Simple session management functions exist
- Database configuration is defined in `src/pat/config.py`
- No models or base classes exist yet

## Requirements
1. Implement connection pooling for efficient resource management
2. Set up async session management
3. Create base models and utility functions for database operations

## Implementation Plan

### 1. Enhance SQLAlchemy Engine Configuration with Connection Pooling
- Update the engine creation in `src/pat/utils/db.py` to include connection pooling parameters
- Configure pool size, overflow, and timeout settings
- Add proper engine disposal on application shutdown

### 2. Improve Async Session Management
- Enhance the existing session management functions
- Implement a session factory with proper configuration
- Add transaction management utilities
- Create functions for common session operations

### 3. Create Base Models and Utility Functions
- Create a base model class with common fields and methods
- Implement utility functions for CRUD operations
- Add helper functions for common database queries
- Set up proper type hints for all database operations

### 4. Add Tests
- Write tests for connection pooling
- Create tests for session management
- Implement tests for base models and utility functions
- Set up database fixtures for testing

## Expected Outcome
A fully configured async SQLAlchemy setup ready for model definitions, with:
- Efficient connection pooling
- Robust async session management
- Reusable base models and utility functions
- Comprehensive test coverage