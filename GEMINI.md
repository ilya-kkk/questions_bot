# GEMINI.md - Project Context for Gemini

## Project Overview

This project is a Python-based Telegram bot designed to help users study for interviews or exams by quizzing them with questions. Users can request a random question, view the answer, and mark questions as "learned" to remove them from the random pool.

The application is fully containerized using Docker and Docker Compose.

### Key Technologies

*   **Language:** Python 3.12
*   **Bot Framework:** `python-telegram-bot`
*   **Database:** PostgreSQL
*   **Containerization:** Docker, Docker Compose
*   **CI/CD:** GitHub Actions for automated deployment.

### Architecture

*   **`app/`**: The main Python application source code.
    *   `bot.py`: The main entry point that starts the Telegram bot.
    *   `handlers.py`: Contains the logic for handling user commands (e.g., `/start`) and button callbacks.
    *   `database.py`: Manages all interactions with the PostgreSQL database.
    *   `config.py`: Loads configuration from environment variables stored in a `.env` file.
*   **`migrations/`**: Contains SQL schema migration files. A Python script (`run_migrations.py`) is used to apply these migrations.
*   **`docker-compose.yaml`**: Defines the services for the application (`app`) and the PostgreSQL database (`postgres`).
*   **`Dockerfile`**: Defines the Docker image for the Python application, installing dependencies from `requirements.txt`.
*   **`import_data.py`**: A utility script to import questions from `raw.json` into the database.
*   **`.github/workflows/deploy.yml`**: A GitHub Actions workflow for automatically deploying the application on a self-hosted runner when changes are pushed to `main` or `master`.

## Building and Running

The project is designed to be run with Docker Compose, which orchestrates the bot application and the PostgreSQL database.

### 1. Initial Setup

Before running the application, you need to create a `.env` file in the project root. This file stores secrets and configuration that should not be committed to version control.

Create a file named `.env` with the following content:

```bash
# .env

# Telegram Bot Token from @BotFather
BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN

# PostgreSQL Credentials
POSTGRES_DB=app_db
POSTGRES_USER=app_user
POSTGRES_PASSWORD=your_strong_password_here
POSTGRES_PORT=5432
```

### 2. Running the Application

1.  **Build and Start Containers:**
    This command will build the Docker image for the bot, start the bot and database containers, and run them in the background.

    ```bash
    docker-compose up --build -d
    ```

2.  **Apply Database Migrations:**
    After the containers are running, apply the initial database schema. This command executes the `run_migrations.py` script inside the running `app` container.

    ```bash
    docker-compose exec app python run_migrations.py
    ```

3.  **Import Questions:**
    Populate the database with questions from the `raw.json` file.

    ```bash
    docker-compose exec app python import_data.py
    ```

The bot should now be running and responsive on Telegram.

### 3. Stopping the Application

To stop the containers, run:

```bash
docker-compose down
```

## Development Conventions

*   **Dependencies:** Python dependencies are managed in `requirements.txt`.
*   **Configuration:** All configuration is managed via environment variables loaded from the `.env` file, as defined in `app/config.py`.
*   **Database:** Schema changes are managed through SQL files in the `migrations/` directory and applied with the `run_migrations.py` script.
*   **Linting/Formatting:** No explicit linting or formatting tools are defined in the project dependencies, but the code generally follows standard Python conventions.
*   **Logging:** The application is configured to log directly to `stdout`, which can be inspected using `docker-compose logs app`.

## Startup Instructions

### General Information
The project is always launched on the server. To execute commands on the server, use SSH CM5 Command.

### CI/CD Process

#### After making code changes:

1. **On the current machine (locally):**
   - Commit the changes:
     ```bash
     git add .
     git commit -m "description of changes"
     git push
     ```

2. **CI/CD will automatically start on the server:**
   - After pushing to the repository, the CI/CD system will automatically process the changes on the server
   - Wait for the CI/CD process to complete (usually a few minutes)

3. **Check container logs on the server:**
   - After CI/CD completes, check container logs on the server via SSH CM5 Command:
     ```bash
     # Example command to check logs
     ssh cm5 "docker logs <container_name>"
     # or for all project containers
     ssh cm5 "docker-compose logs"
     ```

### Executing Commands on the Server

All commands that need to be executed on the server should be run through SSH CM5 Command:
```bash
ssh cm5 "<your_command>"
```

### Important Reminders

- ❗ **DO NOT** run commands directly on the server without SSH
- ✅ **ALWAYS** commit and push changes before checking on the server
- ✅ **ALWAYS** check logs after deployment via CI/CD
- ⏱️ Give CI/CD time to complete the process before checking logs