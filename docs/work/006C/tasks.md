# Tasks for TICKET-006C: Create role-based access control

## Define Role Structure
1. [x] Create a Permission enum in `src/pat/models/role.py`
2. [x] Implement the Role model in `src/pat/models/role.py`
3. [x] Create a many-to-many relationship between roles and permissions
4. [x] Add a relationship between User and Role models
5. [x] Create Alembic migration for the new models

## Implement Permission Checking
6. [x] Create utility functions in `src/pat/utils/auth.py` to check user permissions
7. [x] Implement a permission_required decorator for route functions
8. [x] Add middleware to validate permissions for protected routes
9. [x] Create error responses for permission denied scenarios

## Create Role Assignment Functionality
10. [x] Implement functions to assign roles to users
11. [x] Create endpoints for role management (admin only)
12. [x] Add functionality to update and remove roles
13. [x] Ensure role changes are properly reflected in user permissions

## Schemas and Validation
14. [x] Create Pydantic schemas for Role and Permission in `src/pat/schemas/schemas.py`
15. [x] Implement request/response models for role management endpoints

## Testing
16. [x] Write unit tests for permission checking functions
17. [x] Create integration tests for role assignment functionality
18. [x] Implement tests for role management endpoints
19. [x] Add tests for permission denied scenarios

## Documentation
20. [ ] Update API documentation with role-based access control information
21. [ ] Document available permissions and their meanings
22. [ ] Add examples of role assignment and permission checking
