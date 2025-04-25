# Guidelines for Junie

## Layout
`docs/tickets.md` contains all the upcoming work that needs to be done for the project
`docs/goal.md` contains the long term goal for the project
`docs/work/<ticket_number>` is a directory that contains `plan.md` and `tasks.md` for the ticket.
`docs/work/<ticket_number>/tasks.md` contains the ticket broken down into small tasks
`docs/work/<ticket_number>/plan.md` contains the high level plan for completing the ticket

## Development 
**Important**: strictly follow the instructions below:

* Before working on a ticket always use or generate a `plan.md` file located in `docs/work/<ticket_number>/`
* Use the `docs/work/<ticket_number>/plan.md` file as an input to generate the detailed enumerated task list.
* Store the task list to `docs/work/<ticket_number>/tasks.md`
* Complete one task at a time.
* Immediately After each task is done, mark it as completed in the  `docs/work/<ticket_number>/tasks.md` file
* Before AND after completing a task `make lint` and `make test` MUST BE RUN AND HAVE NO ERRORS BEFORE MOVING ON.
* Tests must be written for each task. 
* Only use classes when absolutely necessary. Prefer functions and functional programming paradigms. 
