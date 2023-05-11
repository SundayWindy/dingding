#!/bin/bash

export DATABASE_URL=${DATABASE_URL:='postgresql://postgres:postgres@postgres:5432/dingding'}


# migrate database
echo 'migrate database'
alembic upgrade head
