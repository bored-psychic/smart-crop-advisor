# Database Migrations

Schema is managed by [Alembic](https://alembic.sqlalchemy.org/). Run from the repo root:

```
alembic upgrade head
```

To see current migration state: `alembic current`. To roll back one step: `alembic downgrade -1`.
