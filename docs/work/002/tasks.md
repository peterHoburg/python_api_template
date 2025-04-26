# Tasks for TICKET-002: Set up SQLAlchemy with async support

## 1. Enhance SQLAlchemy Engine Configuration with Connection Pooling
- [x] 1.1. Update engine creation in `src/pat/utils/db.py` with pool_size, max_overflow, and pool_timeout parameters
- [x] 1.2. Add pool_pre_ping parameter to verify connections before use
- [x] 1.3. Implement engine disposal on application shutdown in main.py
- [x] 1.4. Add logging for connection pool events

## 2. Improve Async Session Management
- [x] 2.1. Enhance session factory with proper configuration options
- [x] 2.2. Create transaction management utilities (commit, rollback, etc.)
- [x] 2.3. Implement session scoping for request lifecycle
- [x] 2.4. Add error handling and retry logic for session operations

## 3. Create Base Models and Utility Functions
- [x] 3.1. Create a base model class with common fields (id, created_at, updated_at)
- [x] 3.2. Implement CRUD utility functions (create, read, update, delete)
- [x] 3.3. Add helper functions for common query patterns
- [x] 3.4. Set up proper type hints for all database operations

## 4. Add Tests
- [x] 4.1. Create database fixtures for testing
- [x] 4.2. Write tests for connection pooling
- [x] 4.3. Implement tests for session management
- [x] 4.4. Create tests for base models and utility functions
