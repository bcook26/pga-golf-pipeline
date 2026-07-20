✅ Modular Python code

---

## ✅ Project Structure Overview

### Key Technologies

- **FastAPI** – Backend API
- **Streamlit** – User Interface
- **Airflow** – ETL Scheduling
- **PySpark** – Data Processing
- **SQL (PostgreSQL/BigQuery)** – Storage & Analytics
- **scikit-learn, PySpark MLlib** – Modeling
- **OpenWeatherMap, GolfNow** – External Data
- **GitHub** – Version Control
- **Email/Push API** – Notifications

---

### 🧩 Component Breakdown

| Component     | Tool(s)                        | Purpose                                                      |
| ------------- | ----------------------------- | ------------------------------------------------------------ |
| Backend API   | FastAPI                       | Serve score recs, weather, course info                       |
| Frontend      | Streamlit                     | UI for users to interact with insights                       |
| Scheduling    | Airflow                       | Schedule daily weather + tee time ingestion                  |
| Processing    | PySpark                       | Scalable transformation, model training                      |
| Storage       | PostgreSQL / BigQuery         | Store scores, courses, user history                          |
| Modeling      | scikit-learn, PySpark MLlib   | Score predictions                                            |
| Notifications | Email / Push API              | Alert users of bad weather or new tee time availability      |
| External APIs | OpenWeatherMap, GolfNow       | Enrich data                                                  |
| Versioning    | GitHub                        | Store all ETL, FastAPI, Streamlit code in standardized style |

---

### 🚦 Project Phases (high level)

| Phase | Focus                            |
| ----- | -------------------------------- |
| 0     | Define scope & minimum features  |
| 0.1   | users should be able to view nearby course info (tee time, weather, scores (if available))
| 0.2   | allow users to upload their score history, check historic trends, optimal tee time based on weather and history
| 1     | Get & store data (ETL basics)    |
| 2     | Transform + analyze with PySpark |
| 3     | Serve results with FastAPI       |
| 4     | Build Streamlit UI               |
| 5     | Schedule ETLs in Airflow         |
| 6     | Add alerts or ML                 |
| 7     | Polish, deploy, and publish      |

---

### 🛠️ Phase Details

#### 🚀 Phase 1: Build Data Foundation (ETL + Storage)
**Goal:** Get your data ingestion working first.

- **Step 1:** Ingest Tee Time & Course Info  
    - Simulate/use GolfNow API or scrape sample tee times  
    - Store in CSV, DuckDB, or PostgreSQL  
    - Include course info: name, par, yardage, location

- **Step 2:** Ingest Weather Data  
    - Use OpenWeatherMap or NOAA API  
    - Pull historical & forecasted data by course location  
    - Store with timestamps

- **Step 3:** Ingest Score Data  
    - Create sample CSV schema for user uploads (Grint/18Birdies)  
    - Fields: user_id, course, hole scores, date, weather if known

> 💡 *Bonus:* Set up basic Airflow DAGs to automate fetching weather and tee time data daily.

---

#### 📊 Phase 2: Process & Analyze with Spark
**Goal:** Process raw data into something useful.

- **Step 4:** Clean & Join Data  
    - Use PySpark to join weather + score history + course info  
    - Clean missing values, standardize course names, convert units

- **Step 5:** Build Basic Score Models  
    - Calculate average score by user & course  
    - Try basic regression to predict score based on:  
        - Temperature  
        - Course  
        - Wind/Weather  
        - Tee time  
        - Hole difficulty (if available)

---

#### 🌐 Phase 3: Expose Data via FastAPI
**Goal:** Serve insights via a clean API.

- **Step 6:** Build FastAPI Endpoints  
    - `/best-tee-times?location=X`: Recommend based on weather + past scores  
    - `/user-summary?id=123`: Average score by course  
    - `/alerts?location=X`: Returns forecast + rain alerts

---

#### 🎛️ Phase 4: Create Streamlit Frontend
**Goal:** Make a simple multi-page UI.

- **Step 7:** Design Streamlit Pages  
    - **Home:** Map or card view of tee times  
    - **Upload Scores:** Upload CSV, trigger pipeline  
    - **Course Insights:** See course summaries and scores  
    - **Weather Alerts:** Show forecast + alerts

> Streamlit can call FastAPI behind the scenes (using `requests`).

---

#### 📅 Phase 5: Automate with Airflow
**Goal:** Schedule everything to run automatically.

- **Step 8:** Schedule Workflows  
    - Run `weather_etl_dag.py` daily at 5am  
    - Run `score_etl_dag.py` when new scores uploaded  
    - Schedule model retraining weekly/monthly

---

#### 🔔 Phase 6: Add Notifications (Optional)
**Goal:** Alert users of high temps, rain, or ideal times.

- **Step 9:** Setup Email or Push Alerts  
    - When rain is forecast for a booked tee time  
    - When a good tee time opens nearby  
    - Use SMTP (email) or integrate with Twilio

---

#### 🔄 Final Phase: Polish & Deploy
**Goal:** Package the project and share it.

- **Step 10:**  
    - Add a README with architecture diagram  
    - Push to GitHub (with dummy data if needed)  
    - Record a demo  
    - Deploy backend (FastAPI) to Render or Railway  
    - Deploy Streamlit UI using Streamlit Community Cloud

---