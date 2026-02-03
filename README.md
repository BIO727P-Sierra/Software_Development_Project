# Software_Development_Project

## Setting up the database

This project is a web-based portal for a direct evolution system. It provides a backend database using PostgreSQL and Docker to allow team members to run the same database environment locally. 

1. First, you will need to have Docker Desktop installed. This will not require PostgreSQL to be installed, as it will run in Docker. 

2. You will need to download the project files, i.e., create a folder for this project and download the schema.sql and docker-compose.yml

3. To start the database change into the project directory and copy across the downloaded files into VSCode or whatever platform you chose eg. 

``` cd path/to/Software_Development_Project ```

and run in your terminal:

``` docker compose up ```

This will pull the PostgreSQL and create a container called direct_evolution_db. This will be created using the schema.sql file to make all the db tables.

4. To access the database, use a PostgreSQL client. For example, using Flask and SQLAlchemy:

``` SQLALCHEMY_DATABSE_URI = "postgresql://sierra:sierra@localhost:5432/direct_evolution" ```

This will run Flask normally, and the backend will connect to the Docker automatically. 

If you would like to access using a GUI such as PgAdmin then use the following connection settings:

```
Host: localhost
Port: 5432
Database: direct_evolution
User: sierra
Password: sierra
```

5. To stop the database, in your terminal you can run:

``` docker compose down```

The database is stored using Docker volumes, and all tables should be within schema.sql.
If the database schema is changed or has been updated, then it will need to be reset. For this run the following code:

``` 
docker compose down -v
docker compose up
```
