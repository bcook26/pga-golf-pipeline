# Golf ETL Project (In Progress)

This project uses FastAPI to create an interface for interacting with different kinds of golf statistics and good to know facts


## Basics of getting started Claude
- I want to build out a full stack application that I can use to track player and course statistics
- data will be ingested from the PGA tour site = "https://www.pgatour.com/" and should follow any security/API guidelines they have in place
- The backend is somewhat put together in PostgreSQL, the API interaction is happening in Python, the frontend should be built in React and fastAPI backend should handle requests from users
- I need to create an airflow job so that I can regularly run ETL to update any player information
- The project should use actions for code formatting, linting, type checking etc. 
- Currently I've only got the ETL portion going which loads players/stats into postgres. 

# Stopped working on pipeline/orchestration (upsert merge failure due to schema change during refactor)

---

## Table of Contents

- [Features](#features)
- [Usage](#usage)
    - [Initial Setup](#initial-setup)
- [Projects Using This Template](#projects-using-this-template)
- [FAQ](#faq)
- [Contributing](#contributing)

---

## Features

- **Robust CI with [GitHub Actions](https://github.com/features/actions):**
    - Unit tests with [PyTest](https://docs.pytest.org) across multiple Python versions (Still in Progress)
    - Type checking via [mypy](https://github.com/python/mypy)
    - Linting with [flake8](https://flake8.pycqa.org/en/latest/)
    - Package Sorting and formatting using [isort](https://pycqa.github.io/isort/) and [black](https://black.readthedocs.io/en/stable/)
- **Automated Dependency Updates: (Not Working yet)**  
    [Dependabot](https://github.blog/2020-06-01-keep-all-your-packages-up-to-date-with-dependabot/) configuration included
- **API Documentation:**  
    Built with [FastAPI](https://fastapi.tiangolo.com/)

---

## Usage

### Initial Setup

1. **Create a new repository/fork**  

2. **Set up a Python 3.8+ virtual environment**

    - Using [`venv`](https://docs.python.org/3/library/venv.html) (built-in):

        ```sh
        python3 -m venv .venv
        source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
        ```

    - Or with [`uv`](https://github.com/astral-sh/uv) (fast alternative):

        ```sh
        uv venv .venv
        source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
        ```

3. **Personalize the repository**

     ```sh
     pip install -r requirements.txt
     ```

4. **Commit and push your changes**  
     Ensure all GitHub Actions jobs pass.
